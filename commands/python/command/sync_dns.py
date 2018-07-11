#!/usr/bin/env python3
from arg_tools import add_namespace_argument
from cluster_rules import cluster_rules
from libs.k8s.kubernetes import Kubernetes
from libs.k8s.kubernetes_utils import KubernetesUtils
import logging


def parse_args(sub_parser):
    subparser = sub_parser.add_parser('sync-dns',
                                      help='Synchronize the dns from the kubernetes services')
    add_namespace_argument(subparser)
    subparser.set_defaults(func=sync_dns_args)


def sync_dns_args(args):
    sync_dns(args.namespace)


def sync_dns(namespace):
    cr = cluster_rules(namespace=namespace)
    if cr.is_local:
        logging.info("Not syncing DNS because you are on local")
        return
    k = Kubernetes(namespace=namespace)
    k_utils = KubernetesUtils(k)
    nb_updated = cr.fill_hostedzone(k_utils.get_services_to_load_balancers_map(
        cr.dual_dns_prefix_annotation_name, cr.ingress_info))
    logging.info('%s DNS mapping updated' % (nb_updated or 'No',))
