#!/usr/bin/env python3
import logging
import sys
import tempfile

from aladdin.lib.arg_tools import add_namespace_argument, container_command
from aladdin.lib.cluster_rules import cluster_rules
from aladdin.commands import sync_ingress, sync_dns
from aladdin.config import load_git_configs
from aladdin.lib.helm_rules import HelmRules
from aladdin.lib.git import Git
from aladdin.lib.k8s.helm import Helm
from aladdin.lib.publish_rules import PublishRules


def parse_args(sub_parser):
    subparser = sub_parser.add_parser(
        "deploy", help="Start the helm chart in non local environments"
    )
    subparser.set_defaults(func=deploy_args)
    add_namespace_argument(subparser)
    subparser.add_argument("project", help="which project to deploy")
    subparser.add_argument("git_ref", help="which git hash or tag or branch to deploy")
    subparser.add_argument(
        "--chart", help="which chart in the project to deploy, defaults to the project name"
    )
    subparser.add_argument(
        "--dry-run",
        "-d",
        action="store_true",
        help="Run the helm as test and don't actually run it",
    )
    subparser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Skip git branch verification if check_branch is enabled on the cluster",
    )
    subparser.add_argument(
        "--force-helm",
        action="store_true",
        help="Have helm force resource update through delete/recreate if needed",
    )
    subparser.add_argument(
        "--repo",
        help="which git repo to pull from, which should be used if it differs from chart name",
    )
    subparser.add_argument(
        "--set-override-values",
        default=[],
        nargs="+",
        help="override values in the values file. Syntax: --set key1=value1 key2=value2 ...",
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
):
    if set_override_values is None:
        set_override_values = []
    with tempfile.TemporaryDirectory() as tmpdirname:
        pr = PublishRules()
        helm = Helm()
        cr = cluster_rules(namespace=namespace)
        helm_chart_path = "{}/{}".format(tmpdirname, chart or project)
        hr = HelmRules(cr, chart or project)
        git_account = load_git_configs()["account"]
        repo = repo or project
        git_url = f"git@github.com:{git_account}/{repo}.git"
        git_ref = Git.extract_hash(git_ref, git_url)

        if not force and cr.check_branch and Git.extract_hash(cr.check_branch, git_url) != git_ref:
            logging.error(
                f"You are deploying hash {git_ref} which does not match branch"
                f" {cr.check_branch} on cluster {cr.cluster_name} for project"
                f" {project}... exiting"
            )
            sys.exit(1)

        helm.pull_packages(project, pr, git_ref, tmpdirname)

        # We need to use --set-string in case the git ref is all digits
        helm_args = ["--set-string", f"deploy.imageTag={git_ref}"]

        # Values precedence is command < cluster rules < --set-override-values
        # Deploy command values
        values = {
            "deploy.ecr": pr.docker_registry,
            "deploy.namespace": namespace,
            "project.name": project,
            "service.certificateArn": cr.service_certificate_arn,
            "service.certificateScope": cr.service_certificate_scope,
            "service.domainName": cr.service_domain_name_suffix,
            "service.clusterCertificateArn": cr.cluster_certificate_arn,
            "service.clusterCertificateScope": cr.cluster_certificate_scope,
            "service.clusterDomainName": cr.cluster_domain_name_suffix,
        }
        # Update with cluster rule values
        values.update(cr.values)
        # Update with --set-override-values
        value_overrides = {k: v for k, v in (value.split("=") for value in set_override_values)}
        values.update(value_overrides)

        if dry_run:
            helm.dry_run(
                hr, helm_chart_path, cr.cluster_name, namespace, helm_args=helm_args, **values
            )
        else:
            helm.start(
                hr,
                helm_chart_path,
                cr.cluster_name,
                namespace,
                force_helm,
                helm_args=helm_args,
                **values,
            )
            sync_ingress.sync_ingress(namespace)
            sync_dns.sync_dns(namespace)
