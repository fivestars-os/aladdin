#!/usr/bin/env python3
from arg_tools import add_namespace_argument
from cluster_rules import cluster_rules
from command import deploy
from libs.k8s.helm import Helm


def parse_args(sub_parser):
    subparser = sub_parser.add_parser(
        "namespace-init",
        help=(
            "Install all projects as defined by namespace_init in"
            " your cluster's config if not already installed"
        ),
    )
    subparser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="don't check if namespace init projects are already installed before installing",
    )
    subparser.add_argument(
        "--helm2",
        action="store_true",
        help="Use helm2 instead of helm3",
    )
    add_namespace_argument(subparser)
    subparser.set_defaults(func=namespace_init_args)


def namespace_init_args(args):
    namespace_init(args.namespace, args.force, args.helm2)


def namespace_init(namespace, force=False, helm2=False):
    helm = Helm(helm2)
    cr = cluster_rules(namespace=namespace)
    namespace_init_projects = cr.namespace_init
    for project in namespace_init_projects:
        project_name = project["project"]
        ref = project["ref"]
        repo = project.get("repo") or project_name
        if not force and helm.release_exists(f"{project_name}-{namespace}", namespace):
            continue
        deploy.deploy(
            project_name,
            ref,
            namespace,
            dry_run=False,
            force=True,
            repo=repo,
            set_override_values=[],
        )
