#!/usr/bin/env python3
from arg_tools import add_namespace_argument
from cluster_rules import cluster_rules
from command import sync_ingress, sync_dns
from helm_rules import HelmRules
from libs.k8s.helm import Helm
from project.project_conf import ProjectConf


def parse_args(sub_parser):
    subparser = sub_parser.add_parser('stop', help='Remove the helm chart in local')
    subparser.set_defaults(func=stop_args)
    add_namespace_argument(subparser)


def stop_args(args):
    stop(args.namespace)


def stop(namespace):
    pc = ProjectConf()
    helm = Helm()

    cr = cluster_rules(namespace=namespace)
    hr = HelmRules(cr, pc.name)

    helm.stop(hr)

    sync_ingress.sync_ingress(namespace)
    sync_dns.sync_dns(namespace)
