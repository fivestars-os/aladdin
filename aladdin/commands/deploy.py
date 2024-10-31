#!/usr/bin/env python3
import logging
import os
import sys
import typing

from aladdin.lib.arg_tools import (
    COMMON_OPTION_PARSER, HELM_OPTION_PARSER, CHART_OPTION_PARSER, container_command
)
from aladdin.lib.cluster_rules import ClusterRules
from aladdin.commands import sync_ingress
from aladdin.config import load_git_configs
from aladdin.lib.arg_tools import expand_namespace
from aladdin.lib.helm_rules import HelmRules
from aladdin.lib.git import Git, clone_and_checkout
from aladdin.lib.k8s.helm import Helm
from aladdin.lib.utils import working_directory
from aladdin.lib.project_conf import ProjectConf


def parse_args(sub_parser):
    subparser = sub_parser.add_parser(
        "deploy", help="Start the helm chart in non local environments",
        parents=[COMMON_OPTION_PARSER, HELM_OPTION_PARSER, CHART_OPTION_PARSER]
    )
    subparser.set_defaults(func=deploy)
    subparser.add_argument("project", help="which project to deploy")
    subparser.add_argument("git_ref", help="which git hash or tag or branch to deploy")
    subparser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Skip git branch verification if check_branch is enabled on the cluster",
    )
    subparser.add_argument(
        "--repo",
        help="which git repo to pull from, which should be used if it differs from chart name",
    )


@container_command
@expand_namespace
def deploy(
    project,
    git_ref,
    namespace,
    chart=None,
    dry_run=False,
    force=False,
    force_helm=False,
    repo=None,
    set_override_values: typing.List[str] = None,
    values_files=None
):
    chart = chart or project
    repo = repo or project
    if set_override_values is None:
        set_override_values = []
    helm = Helm()
    cr = ClusterRules(namespace=namespace)
    cluster_code = os.environ["CLUSTER_CODE"]
    git_account = load_git_configs()["account"]
    git_url = f"git@github.com:{git_account}/{repo}.git"
    git_ref = Git.extract_hash(git_ref, git_url)

    if not force and cr.check_branch and Git.extract_hash("HEAD", git_url) != git_ref:
        logging.error(
            f"You are deploying hash {git_ref} which does not match default branch"
            f" on cluster {cr.cluster_domain_name} for project {project}... exiting"
        )
        sys.exit(1)

    with clone_and_checkout(git_ref, repo) as tmpdirname:
        with working_directory(tmpdirname):
            helm_chart_path = ProjectConf().get_helm_chart_path(chart)

        helm_args = [
            f"--values=aladdin://{cluster_code}",
        ]
        values = HelmRules.get_helm_values()
        # Add user-specified values files
        for file_path in (values_files or []):
            helm_args.append(f"--values={os.path.join(helm_chart_path, 'values', file_path)}")
        # Update with --set-override-values
        values.update(dict(value.split("=") for value in set_override_values))

        helm.upgrade(
            HelmRules.get_release_name(chart),
            helm_chart_path,
            [],
            namespace,
            force=force_helm,
            dry_run=dry_run,
            helm_args=helm_args,
            **values,
        )
        if not dry_run:
            sync_ingress.sync_ingress(namespace)
