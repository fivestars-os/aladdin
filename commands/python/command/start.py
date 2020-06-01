#!/usr/bin/env python3
from arg_tools import add_namespace_argument
from cluster_rules import cluster_rules
from command import sync_ingress, sync_dns
from helm_rules import HelmRules
from libs.k8s.helm import Helm
from project.project_conf import ProjectConf


def parse_args(sub_parser):
    subparser = sub_parser.add_parser("start", help="Start the helm chart in local")
    subparser.set_defaults(func=start_args)
    add_namespace_argument(subparser)
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
    start(args.namespace, args.dry_run, args.with_mount, args.force_helm, args.set_override_values)


def start(namespace, dry_run=False, with_mount=False, force_helm=False, set_override_values=None):
    if set_override_values is None:
        set_override_values = []
    pc = ProjectConf()
    helm = Helm()

    cr = cluster_rules(namespace=namespace)
    hr = HelmRules(cr, pc.name)

    # Values precedence is command < cluster rules < --set-override-values
    # Start command values
    values = {
        "deploy.withMount": with_mount,
        "deploy.mountPath": pc.mount_path,
        "deploy.imageTag": "local",
    }
    # Update with cluster rule values
    values.update(cr.values)
    # Update with --set-override-values
    value_overrides = {k: v for k, v in (value.split("=") for value in set_override_values)}
    values.update(value_overrides)

    if dry_run:
        helm.dry_run(hr, pc.helm_path, cr.cluster_name, namespace, **values)
    else:
        helm.start(hr, pc.helm_path, cr.cluster_name, namespace, force_helm, **values)
        sync_ingress.sync_ingress(namespace)
        sync_dns.sync_dns(namespace)
