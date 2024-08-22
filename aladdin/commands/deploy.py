#!/usr/bin/env python3
import logging
import os
import sys
import tempfile

from aladdin.lib.arg_tools import (
    COMMON_OPTION_PARSER, HELM_OPTION_PARSER, CHART_OPTION_PARSER, container_command
)
from aladdin.lib.cluster_rules import ClusterRules
from aladdin.commands import sync_ingress
from aladdin.config import load_git_configs
from aladdin.lib.helm_rules import HelmRules
from aladdin.lib.git import Git
from aladdin.lib.k8s.helm import Helm
from aladdin.lib.utils import working_directory
from aladdin.lib.project_conf import ProjectConf


def parse_args(sub_parser):
    subparser = sub_parser.add_parser(
        "deploy", help="Start the helm chart in non local environments",
        parents=[COMMON_OPTION_PARSER, HELM_OPTION_PARSER, CHART_OPTION_PARSER]
    )
    subparser.set_defaults(func=deploy_args)
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


def deploy_args(args):
    deploy(
        args.project,
        args.git_ref,
        args.namespace,
        args.chart,
        args.dry_run,
        args.force,
        args.force_helm,
        args.repo,
        args.set_override_values,
        args.values_files
    )


@container_command
def deploy(
    project,
    git_ref,
    namespace,
    chart=None,
    dry_run=False,
    force=False,
    force_helm=False,
    repo=None,
    set_override_values=None,
    values_files=None
):
    chart = chart or project
    repo = repo or project
    if set_override_values is None:
        set_override_values = []
    helm = Helm()
    cr = ClusterRules(namespace=namespace)
    git_account = load_git_configs()["account"]
    git_url = f"git@github.com:{git_account}/{repo}.git"
    git_ref = Git.extract_hash(git_ref, git_url)

    if not force and cr.check_branch and Git.extract_hash("HEAD", git_url) != git_ref:
        logging.error(
            f"You are deploying hash {git_ref} which does not match default branch"
            f" on cluster {cr.cluster_domain_name} for project {project}... exiting"
        )
        sys.exit(1)

    with tempfile.TemporaryDirectory() as tmpdirname:
        Git.clone(git_url, tmpdirname)
        Git.checkout(tmpdirname, git_ref)
        with working_directory(tmpdirname):
            helm_chart_path = ProjectConf().get_helm_chart_path(chart)

        # We need to use --set-string in case the git ref is all digits
        helm_args = ["--set-string", f"deploy.imageTag={git_ref}"]
        values = HelmRules.get_helm_values()
        values.update({
            "project.name": project,
        })
        # Add user-specified values files
        if values_files:
            for file_path in values_files:
                helm_args.append(f"--values={os.path.join(helm_chart_path, 'values', file_path)}")
        # Update with --set-override-values
        values.update(dict(value.split("=") for value in set_override_values))

        helm.upgrade(
            HelmRules.get_release_name(chart),
            helm_chart_path,
            cr.values_files,
            namespace,
            force=force_helm,
            dry_run=dry_run,
            helm_args=helm_args,
            **values,
        )
        if not dry_run:
            sync_ingress.sync_ingress(namespace)
