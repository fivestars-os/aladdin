#!/usr/bin/env python3
import os

from arg_tools import add_namespace_argument
from cluster_rules import cluster_rules
from command import sync_ingress, sync_dns
from helm_rules import HelmRules
from libs.k8s.helm import Helm
from project.project_conf import ProjectConf


def parse_args(sub_parser):
    subparser = sub_parser.add_parser("stop", help="Remove the helm chart in local")
    subparser.set_defaults(func=stop_args)
    add_namespace_argument(subparser)
    subparser.add_argument(
        "--chart",
        action="append",
        dest="charts",
        help="Stop only these charts (may be specified multiple times)",
    )
    subparser.add_argument(
        "--helm2",
        action="store_true",
        help="Use helm2 instead of helm3",
    )


def stop_args(args):
    stop(args.namespace, args.charts, args.helm2)


def stop(namespace, charts, helm2=False):
    pc = ProjectConf()
    helm = Helm(helm2)

    cr = cluster_rules(namespace=namespace)

    if charts is None:
        # Stop each of the project's charts
        charts = [os.path.basename(chart_path) for chart_path in pc.get_helm_chart_paths()]

    sync_required = False
    try:
        for chart_path in pc.get_helm_chart_paths():
            chart_name = os.path.basename(chart_path)
            if chart_name in charts:
                hr = HelmRules(cr, chart_name)
                helm.stop(hr, namespace)
                sync_required = True
    finally:
        # Sync if any helm.stop() call succeeded, even if a subsequent one failed
        if sync_required:
            sync_ingress.sync_ingress(namespace)
            sync_dns.sync_dns(namespace)
