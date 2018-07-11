#!/usr/bin/env python3
from arg_tools import add_namespace_argument
from cluster_rules import cluster_rules
from libs.k8s.kubernetes import Kubernetes
from libs.k8s.ingress import build_ingress
import logging


def parse_args(sub_parser):
    subparser = sub_parser.add_parser('sync-ingress',
                                      help='Synchronize ingress to put services behind ingress')
    add_namespace_argument(subparser)
    subparser.set_defaults(func=sync_ingress_args)


def sync_ingress_args(args):
    sync_ingress(args.namespace)


def sync_ingress(namespace):
    cr = cluster_rules(namespace=namespace)
    ingress_info = cr.ingress_info
    if ingress_info and ingress_info['use_ingress_per_namespace']:
        k = Kubernetes(namespace=namespace)
        ingress_list = k.get_ingresses()
        ingress = build_ingress(k.get_services(), cr.service_dns_suffix,
            cr.dual_dns_prefix_annotation_name, ingress_info)
        if any(i for i in ingress_list if i.metadata.name == ingress.metadata.name):
            # update existing ingress
            k.update_ingress(ingress.metadata.name, ingress)
            logging.info("Successfully updated ingress")
        else:
            # create new ingress
            k.create_ingress(ingress)
            logging.info("Successfully created ingress")
