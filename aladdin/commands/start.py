#!/usr/bin/env python3
import os

from aladdin.lib.arg_tools import (
    COMMON_OPTION_PARSER, HELM_OPTION_PARSER, CHARTS_OPTION_PARSER, container_command
)
from aladdin.lib.cluster_rules import ClusterRules
from aladdin.commands import sync_ingress, sync_dns
from aladdin.lib.helm_rules import HelmRules
from aladdin.lib.k8s.helm import Helm
from aladdin.lib.project_conf import ProjectConf


def parse_args(sub_parser):
    subparser = sub_parser.add_parser(
        "start", help="Start the helm chart in local",
        parents=[COMMON_OPTION_PARSER, HELM_OPTION_PARSER, CHARTS_OPTION_PARSER]
    )
    subparser.set_defaults(func=start_args)


def start_args(args):
    start(
        args.namespace,
        args.charts,
        args.dry_run,
        args.force_helm,
        args.set_override_values,
        args.values_files,
    )


@container_command
def start(
    namespace,
    charts=None,
    dry_run=False,
    force_helm=False,
    set_override_values=None,
    values_files=None,
):
    if set_override_values is None:
        set_override_values = []
    pc = ProjectConf()
    helm = Helm()

    cr = ClusterRules(namespace=namespace)

    if not charts:
        # Start each of the project's charts
        charts = [os.path.basename(chart_path) for chart_path in pc.get_helm_chart_paths()]

    values = HelmRules.get_helm_values()
    helm_args = []
    values.update({
        "deploy.imageTag": "local",
    })
    # Update with --set-override-values
    values.update(dict(value.split("=") for value in set_override_values))

    try:
        for chart_path in pc.get_helm_chart_paths():
            chart_name = os.path.basename(chart_path)
            # Add user-specified values files
            if values_files:
                for file_path in values_files:
                    helm_args.append(f"--values={os.path.join(chart_path, 'values', file_path)}")
            if chart_name in charts:
                release_name = HelmRules.get_release_name(chart_name)
                helm.upgrade(
                    release_name, chart_path, cr.cluster_name, namespace,
                    force=force_helm, dry_run=dry_run, helm_args=helm_args, **values
                )
    finally:
        # Sync if any helm.start() call succeeded, even if a subsequent one failed
        if not dry_run:
            sync_ingress.sync_ingress(namespace)
            sync_dns.sync_dns(namespace)
