import argparse
import logging
import os
import subprocess
from contextlib import suppress
from urllib.parse import urlparse, parse_qsl
from typing import Optional

import yaml

from aladdin.config import PROJECT_ROOT, load_git_configs
from aladdin.lib.arg_tools import (
    CHART_OPTION_PARSER,
    COMMON_OPTION_PARSER,
    expand_namespace,
    container_command,
)
from aladdin.lib.cluster_rules import ClusterRules
from aladdin.lib.git import Git, clone_and_checkout
from aladdin.lib.helm_rules import HelmRules
from aladdin.lib.k8s.helm import Helm
from aladdin.lib.project_conf import ProjectConf
from aladdin.lib.utils import working_directory, strtobool


def parse_args(sub_parser):
    parser: argparse.ArgumentParser = sub_parser.add_parser(
        "helm-values",
        help="Given a git ref, compute helm values for the given cluster, repo, and chart",
        description="Command setup to be used as a helm downloader plugin using the 'aladdin://' protocol",
        parents=[COMMON_OPTION_PARSER, CHART_OPTION_PARSER],
    )
    parser.set_defaults(func=helm_values)
    parser.add_argument("uri", help="aladdin://CLUSTER_CODE/REPO_NAME?chart=chart_name&git-ref=ref")
    parser.add_argument(
        "--git-ref",
        help="which git hash or tag or branch to get values from",
    )
    parser.add_argument(
        "-A",
        "--all",
        help="show all values, including default values",
        dest="all_values",
        action="store_true",
        default=True,
    )
    parser.add_argument(
        "-o",
        "--output",
        help="output values to a file",
        dest="output",
        default=None,
    )


@container_command
@expand_namespace
def helm_values(
    namespace: str,
    uri: str,
    git_ref: str = None,
    chart: str = None,
    all_values: bool = True,
    output: str = None,
):
    uri = urlparse(uri)
    params = dict(parse_qsl(uri.query, keep_blank_values=True))
    os.environ["CLUSTER_CODE"] = uri.netloc
    repo_name = uri.path.lstrip("/")
    ClusterRules(namespace=namespace)
    git_account = load_git_configs()["account"]
    git_ref = Git.extract_hash(
        git_ref or params.get("git-ref") or Git.get_full_hash(),
        f"git@github.com:{git_account}/{repo_name}.git" if repo_name else None
    )
    if "all" in params:
        if params.get("all") == "":
            params["all"] = "true"
        all_values = strtobool(params.get("all"))

    with clone_and_checkout(git_ref, repo_name, debug=HelmRules.debug) as repo_dir:
        current_chart_name = get_current_chart_name()
        with working_directory(repo_dir):
            chart_path = os.path.abspath(
                ProjectConf().get_helm_chart_path(chart or params.get("chart") or current_chart_name)
            )
            command = [
                "helm",
                "template",
                str(PROJECT_ROOT / "aladdin/charts/merger"),
                f"--namespace={namespace}"
            ]
            if all_values:
                command.append(f"--values={chart_path}/values.yaml")

            command = Helm().prepare_command(
                command,
                chart_path,
                ClusterRules().values_files,
                ClusterRules().namespace,
                # We need to use --set-string in case the git ref is all digits
                helm_args=["--set-string", f"deploy.imageTag={git_ref}"],
                **HelmRules.get_helm_values(),
            )

            logging.info("Executing: %s", " ".join(command))
            result = subprocess.run(
                command,
                capture_output=output is not None,
                check=True,
                encoding="utf-8",
            )
            if output:
                with open(output, "w") as outputfile:
                    outputfile.write(result.stdout)
                logging.info("Values saved in: %s", output)


def get_current_chart_name() -> Optional[str]:
    with suppress(FileNotFoundError):
        with open("Chart.yaml") as chart_manifest:
            return yaml.safe_load(chart_manifest)["name"]
