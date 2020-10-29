#!/usr/bin/env python3
from cluster_rules import cluster_rules
from command import deploy
from libs.k8s.helm import Helm


def parse_args(sub_parser):
    subparser = sub_parser.add_parser(
        "cluster-init",
        help=(
            "Install all projects as defined by cluster_init in"
            " your cluster's config if not already installed"
        ),
    )
    subparser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="don't check if cluster init projects are already installed before installing",
    )
    subparser.add_argument(
        "--helm2",
        action="store_true",
        help="Use helm2 instead of helm3",
    )
    subparser.set_defaults(func=cluster_init_args)


def cluster_init_args(args):
    cluster_init(args.force, args.helm2)


def cluster_init(force=False, helm2=False):
    helm = Helm(helm2)
    cr = cluster_rules()
    cluster_init_projects = cr.cluster_init
    for project in cluster_init_projects:
        project_name = project["project"]
        ref = project["ref"]
        project_namespace = project["namespace"]
        repo = project.get("repo") or project_name
        if not force and helm.release_exists(f"{project_name}-{project_namespace}"):
            continue
        deploy.deploy(
            project_name,
            ref,
            project_namespace,
            dry_run=False,
            force=True,
            repo=repo,
            set_override_values=[],
        )
