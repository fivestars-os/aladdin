#!/usr/bin/env python3
from arg_tools import add_namespace_argument
from cluster_rules import cluster_rules
from libs.aws.dns_mapping import fill_hostedzone
from libs.k8s.kubernetes import Kubernetes
from libs.k8s.kubernetes_utils import KubernetesUtils
import logging


def parse_args(sub_parser):
    subparser = sub_parser.add_parser(
        "sync-dns", help="Synchronize the dns from the kubernetes services"
    )
    add_namespace_argument(subparser)
    subparser.set_defaults(func=sync_dns_args)


def sync_dns_args(args):
    sync_dns(args.namespace)


def sync_dns(namespace):
    cr = cluster_rules(namespace=namespace)
    if cr.is_local:
        logging.info("Not syncing DNS because you are on local")
        return

    k_utils = KubernetesUtils(Kubernetes(namespace=namespace))

    service_loadbalancers = k_utils.get_services_to_load_balancers_map(
        cr.dual_dns_prefix_annotation_name, cr.ingress_info
    )

    # Apply our dns to the service names
    service_hostnames_to_loadbalancers = {
        f"{service_name}.{cr.namespace_domain_name}": loadbalancer_hostname
        for service_name, loadbalancer_hostname in service_loadbalancers.items()
    }

    nb_updated = fill_hostedzone(
        cr.boto,
        cr.cluster_domain_name,
        cr.namespace_domain_name,
        service_hostnames_to_loadbalancers,
    )

    logging.info("%s DNS mapping updated" % (nb_updated or "No",))
