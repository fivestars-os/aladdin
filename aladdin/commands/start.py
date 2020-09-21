#!/usr/bin/env python3
import os

from aladdin.arg_tools import add_namespace_argument
from aladdin.cluster_rules import cluster_rules
from aladdin.commands import sync_ingress, sync_dns
from aladdin.helm_rules import HelmRules
from aladdin.lib.k8s.helm import Helm
from aladdin.lib.project_conf import ProjectConf


def parse_args(sub_parser):
    subparser = sub_parser.add_parser("start", help="Start the helm chart in local")
    subparser.set_defaults(func=start_args)
    add_namespace_argument(subparser)
    subparser.add_argument(
        "--chart",
        action="append",
        dest="charts",
        help="Only start these charts (may be specified multiple times)",
    )
    subparser.add_argument(
        "--dry-run",
        "-d",
        action="store_true",
        help="Run the helm as test and don't actually run it",
    )
    subparser.add_argument(
        "--with-mount",
        "-m",
        action="store_true",
        help="Mount user's host's project repo onto container",
    )
    subparser.add_argument(
        "--force-helm",
        action="store_true",
        help="Have helm force resource update through delete/recreate if needed",
    )
    subparser.add_argument(
        "--set-override-values",
        default=[],
        nargs="+",
        help="override values in the values file. Syntax: --set key1=value1 key2=value2 ...",
    )


def start_args(args):
    start(
        args.namespace,
        args.charts,
        args.dry_run,
        args.with_mount,
        args.force_helm,
        args.set_override_values,
    )


def start(
    namespace,
    charts=None,
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

    if charts is None:
        # Start each of the project's charts
        charts = [os.path.basename(chart_path) for chart_path in pc.get_helm_chart_paths()]

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
    # Update with --set-override-values
    value_overrides = {k: v for k, v in (value.split("=") for value in set_override_values)}
    values.update(value_overrides)

    sync_required = False
    try:
        for chart_path in pc.get_helm_chart_paths():
            chart_name = os.path.basename(chart_path)
            if chart_name in charts:
                hr = HelmRules(cr, chart_name)
                if dry_run:
                    helm.dry_run(hr, chart_path, cr.cluster_name, namespace, **values)
                else:
                    helm.start(hr, chart_path, cr.cluster_name, namespace, force_helm, **values)
                    sync_required = True
    finally:
        # Sync if any helm.start() call succeeded, even if a subsequent one failed
        if sync_required:
            sync_ingress.sync_ingress(namespace)
            sync_dns.sync_dns(namespace)
