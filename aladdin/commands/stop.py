#!/usr/bin/env python3
import os

from aladdin.lib.arg_tools import CHARTS_OPTION_PARSER, COMMON_OPTION_PARSER, container_command
from aladdin.lib.cluster_rules import ClusterRules
from aladdin.commands import sync_ingress, sync_dns
from aladdin.lib.helm_rules import HelmRules
from aladdin.lib.k8s.helm import Helm
from aladdin.lib.project_conf import ProjectConf


def parse_args(sub_parser):
    subparser = sub_parser.add_parser(
        "stop", help="Remove the helm chart in local",
        parents=[COMMON_OPTION_PARSER, CHARTS_OPTION_PARSER]
    )
    subparser.set_defaults(func=stop_args)


def stop_args(args):
    stop(args.namespace, args.charts)


@container_command
def stop(namespace, charts):
    pc = ProjectConf()
    helm = Helm()

    cr = ClusterRules(namespace=namespace)

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
