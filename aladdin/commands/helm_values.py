import argparse
import logging
import os
import subprocess
import sys
import tempfile
from urllib.parse import urlparse, parse_qsl

from aladdin.config import PROJECT_ROOT, load_git_configs
from aladdin.lib.arg_tools import (
    CHART_OPTION_PARSER,
    COMMON_OPTION_PARSER,
    expand_namespace,
    container_command,
)
from aladdin.lib.aws.certificate import (
    get_cluster_certificate_arn,
    get_service_certificate_arn,
)
from aladdin.lib.cluster_rules import ClusterRules
from aladdin.lib.git import Git
from aladdin.lib.k8s.helm import Helm
from aladdin.lib.project_conf import ProjectConf
from aladdin.lib.publish_rules import PublishRules
from aladdin.lib.utils import working_directory


def parse_args(sub_parser):
    parser: argparse.ArgumentParser = sub_parser.add_parser(
        "helm-values",
        help="Given a git ref, compute helm values for the given cluster, repo, and chart",
        description="Command setup to be used as a helm downloader plugin using the 'aladdin://' protocol",
        parents=[COMMON_OPTION_PARSER, CHART_OPTION_PARSER],
    )
    parser.set_defaults(func=helm_values)
    parser.add_argument(
        "uri",
        help="aladdin://CLUSTER_CODE/REPO_NAME?chart=chart_name"
    )
    parser.add_argument(
        "git-ref",
        help="which git hash or tag or branch to get values from",
    )
    parser.add_argument(
        "-A", "--all",
        help="show all values, including default values",
        dest="all_values",
        action="store_true",
    )


@container_command
@expand_namespace
def helm_values(uri: str, namespace: str, git_ref: str, chart: str = None, all_values: bool = False):
    uri = urlparse(uri)
    params = dict(parse_qsl(uri.query))
    os.environ["CLUSTER_CODE"] = uri.netloc
    REPO_NAME = uri.path.lstrip("/")
    ClusterRules(namespace=namespace)
    GIT_ACCOUNT = load_git_configs()["account"]
    git_url = f"git@github.com:{GIT_ACCOUNT}/{REPO_NAME}.git"
    git_ref = Git.extract_hash(git_ref, git_url)

    values = {
        "deploy.ecr": PublishRules().docker_registry,
        "deploy.namespace": ClusterRules().namespace,
        "service.certificateScope": ClusterRules().service_certificate_scope,
        "service.domainName": ClusterRules().service_domain_name_suffix,
        "service.clusterCertificateScope": ClusterRules().cluster_certificate_scope,
        "service.clusterDomainName": ClusterRules().cluster_domain_name_suffix,
        "service.clusterName": ClusterRules().cluster_domain_name,  # aka root_dns
    }
    if ClusterRules().certificate_lookup:
        values.update(
            {
                "service.certificateArn": get_service_certificate_arn(),
                "service.clusterCertificateArn": get_cluster_certificate_arn(),
            }
        )
    values.update(ClusterRules().values)

    with tempfile.TemporaryDirectory() as tmpdirname:
        try:
            Git.clone(git_url, tmpdirname)
        except subprocess.CalledProcessError:
            logging.warn(f"Could not clone repo {git_url}. Does it exist?")
            return sys.exit(1)
        try:
            Git.checkout(tmpdirname, git_ref)
        except subprocess.CalledProcessError:
            logging.warn(
                f"Could not checkout to ref '{git_ref}' in repo {git_url}. Have you pushed it to remote?"
            )
            return sys.exit(1)

        with working_directory(tmpdirname):
            values["project.name"] = ProjectConf().name
            CHART_PATH = os.path.relpath(
                ProjectConf().get_helm_chart_path(chart or params.get("chart"))
            )
            args = []
            if all_values:
                args.append(f"--values={CHART_PATH}/values.yaml")
            args.extend([
                f"--values={values_file}"
                for values_file in Helm().find_values(
                    CHART_PATH, ClusterRules().cluster_name, ClusterRules().namespace
                )
            ])
            for key, value in values.items():
                args.extend(["--set", f"{key}={value}"])

            args.extend(["--set-string", f"deploy.imageTag={git_ref}"])
            command = [
                "helm",
                "template",
                str(PROJECT_ROOT / "aladdin/charts/merger"),
                *args,
            ]
            logging.info("Executing: %s", " ".join(command))
            subprocess.run(
                command,
                capture_output=False,
                check=True,
            )
