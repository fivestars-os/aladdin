#!/usr/bin/env python3
import os

from aladdin.lib.arg_tools import COMMON_OPTION_PARSER, HELM_OPTION_PARSER, container_command
from aladdin.lib.cluster_rules import cluster_rules
from aladdin.commands import sync_ingress, sync_dns
from aladdin.lib.helm_rules import HelmRules
from aladdin.lib.k8s.helm import Helm
from aladdin.lib.project_conf import ProjectConf


def parse_args(sub_parser):
    subparser = sub_parser.add_parser(
        "start", help="Start the helm chart in local",
        parents=[COMMON_OPTION_PARSER, HELM_OPTION_PARSER]
    )
    subparser.set_defaults(func=start_args)
    subparser.add_argument(
        "--with-mount",
        "-m",
        action="store_true",
        help="Mount user's host's project repo onto container",
    )


def start_args(args):
    start(
        args.namespace,
        args.chart,
        args.dry_run,
        args.with_mount,
        args.force_helm,
        args.set_override_values,
    )


@container_command
def start(
    namespace,
    chart=None,
    dry_run=False,
    with_mount=False,
    force_helm=False,
    set_override_values=None,
):
    if set_override_values is None:
        set_override_values = []
    pc = ProjectConf()
    helm = Helm()

    cr = cluster_rules(namespace=namespace)

    if not chart:
        # Start each of the project's charts
        charts = [os.path.basename(chart_path) for chart_path in pc.get_helm_chart_paths()]
    else:
        charts = [chart]

    # Values precedence is command < cluster rules < --set-override-values
    # Start command values
    values = {
        "deploy.imageTag": "local",
        "deploy.mountPath": pc.mount_path,
        "deploy.namespace": namespace,
        "deploy.withMount": with_mount,
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
    # Update with user-specified values file
    values_files = [
        f"--values={file_name}" for file_name in set_override_values
        if "=" not in file_name
    ]
    # Update with --set-override-values
    value_overrides = {
        k: v for k, v in
        (value.split("=") for value in set_override_values if "=" in value)
    }
    values.update(value_overrides)

    sync_required = False
    try:
        for chart_path in pc.get_helm_chart_paths():
            chart_name = os.path.basename(chart_path)
            if chart_name in charts:
                hr = HelmRules(cr, chart_name)
                if dry_run:
                    helm.dry_run(
                        hr, chart_path, cr.cluster_name, namespace,
                        helm_args=values_files, **values
                    )
                else:
                    helm.start(
                        hr, chart_path, cr.cluster_name, namespace,
                        force=force_helm, helm_args=values_files, **values
                    )
                    sync_required = True
    finally:
        # Sync if any helm.start() call succeeded, even if a subsequent one failed
        if sync_required:
            sync_ingress.sync_ingress(namespace)
            sync_dns.sync_dns(namespace)
