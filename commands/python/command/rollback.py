#!/usr/bin/env python3
from arg_tools import add_namespace_argument
from cluster_rules import cluster_rules
from command import sync_ingress, sync_dns
from helm_rules import HelmRules
from libs.k8s.helm import Helm


def parse_args(sub_parser):
    subparser = sub_parser.add_parser("rollback", help="Go back to a previous deployment")
    subparser.set_defaults(func=rollback_args)
    add_namespace_argument(subparser)
    subparser.add_argument("project", help="which project to undeploy")
    subparser.add_argument(
        "--num-versions", type=int, default=1, help="how many versions to rollback, defaults to 1"
    )


def rollback_args(args):
    rollback(args.project, args.num_versions, args.namespace)


def rollback(project, num_versions, namespace):
    helm = Helm()

    cr = cluster_rules(namespace=namespace)
    hr = HelmRules(cr, project)

    helm.rollback_relative(hr, num_versions)

    sync_ingress.sync_ingress(namespace)
    sync_dns.sync_dns(namespace)
