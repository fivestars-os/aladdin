#!/usr/bin/env python3
from arg_tools import add_namespace_argument
from cluster_rules import cluster_rules
from command import sync_ingress, sync_dns
from helm_rules import HelmRules
from libs.k8s.helm import Helm


def parse_args(sub_parser):
    subparser = sub_parser.add_parser(
        "undeploy", help="Remove the helm chart in non local environments"
    )
    subparser.set_defaults(func=undeploy_args)
    add_namespace_argument(subparser)
    subparser.add_argument("project", help="which project to undeploy")
    subparser.add_argument(
        "--chart",
        help="which chart in the project to undeploy, defaults to the project name"
    )
    subparser.add_argument(
        "--helm2",
        action="store_true",
        help="Use helm2 instead of helm3",
    )


def undeploy_args(args):
    undeploy(args.project, args.namespace, args.chart, args.helm2)


def undeploy(project, namespace, chart=None, helm2=False):
    helm = Helm(helm2)

    cr = cluster_rules(namespace=namespace)
    hr = HelmRules(cr, chart or project)

    helm.stop(hr, namespace)

    sync_ingress.sync_ingress(namespace)
    sync_dns.sync_dns(namespace)
