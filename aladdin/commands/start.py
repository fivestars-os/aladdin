#!/usr/bin/env python3
import logging
import os
import sys

from aladdin.lib.arg_tools import (
    COMMON_OPTION_PARSER, HELM_OPTION_PARSER, CHARTS_OPTION_PARSER, container_command
)
from aladdin.lib.cluster_rules import cluster_rules
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

    cr = cluster_rules(namespace=namespace)

    if not charts:
        # Start each of the project's charts
        charts = [os.path.basename(chart_path) for chart_path in pc.get_helm_chart_paths()]

    # Values precedence is command < cluster rules < --set-override-values
    # Start command values
    values = {
        "deploy.imageTag": "local",
        "deploy.namespace": namespace,
        "project.name": pc.name,
        "service.certificateArn": cr.service_certificate_arn,
        "service.certificateScope": cr.service_certificate_scope,
        "service.domainName": cr.service_domain_name_suffix,
        "service.clusterCertificateArn": cr.cluster_certificate_arn,
        "service.clusterCertificateScope": cr.cluster_certificate_scope,
        "service.clusterDomainName": cr.cluster_domain_name_suffix,
    }
    # Update with cluster rule values
    values.update(cr.values)
    helm_args = []
    # Update with --set-override-values
    values.update(dict(value.split("=") for value in set_override_values))

    sync_required = False
    try:
        for chart_path in pc.get_helm_chart_paths():
            chart_name = os.path.basename(chart_path)
            # Add user-specified values files
            if values_files:
                for file_path in values_files:
                    helm_args.append(f"--values={os.path.join(chart_path, 'values', file_path)}")
            if chart_name in charts:
                hr = HelmRules(cr, chart_name)
                if dry_run:
                    helm.dry_run(
                        hr, chart_path, cr.cluster_name, namespace,
                        helm_args=helm_args, **values
                    )
                else:
                    helm.start(
                        hr, chart_path, cr.cluster_name, namespace,
                        force=force_helm, helm_args=helm_args, **values
                    )
                    sync_required = True
    finally:
        # Sync if any helm.start() call succeeded, even if a subsequent one failed
        if sync_required:
            sync_ingress.sync_ingress(namespace)
            sync_dns.sync_dns(namespace)
