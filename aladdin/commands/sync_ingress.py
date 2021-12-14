import logging

from aladdin.lib.arg_tools import add_namespace_argument, container_command
from aladdin.lib.cluster_rules import ClusterRules
from aladdin.lib.k8s.kubernetes import Kubernetes
from aladdin.lib.k8s.ingress import build_ingress


def parse_args(sub_parser):
    subparser = sub_parser.add_parser(
        "sync-ingress", help="Synchronize ingress to put services behind ingress"
    )
    add_namespace_argument(subparser)
    subparser.set_defaults(func=sync_ingress_args)


def sync_ingress_args(args):
    sync_ingress(args.namespace)


@container_command
def sync_ingress(namespace):
    cr = ClusterRules(namespace=namespace)
    ingress_info = cr.ingress_info
    if ingress_info and ingress_info["use_ingress_per_namespace"]:
        k = Kubernetes(namespace=namespace)
        ingress_list = k.get_ingresses()
        ingress = build_ingress(
            k.get_services(),
            cr.service_domain_name_suffix,
            cr.dual_dns_prefix_annotation_name,
            ingress_info,
        )
        if any(i for i in ingress_list if i.metadata.name == ingress.metadata.name):
            # update existing ingress
            if cr.is_local:
                k.delete_ingress(ingress.metadata.name)
                k.create_ingress(ingress)
            else:
                k.update_ingress(ingress.metadata.name, ingress)
            logging.info("Successfully updated ingress")
        else:
            # create new ingress
            k.create_ingress(ingress)
            logging.info("Successfully created ingress")
