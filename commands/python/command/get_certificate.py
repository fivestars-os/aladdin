#!/usr/bin/env python3
from cluster_rules import cluster_rules
from arg_tools import add_namespace_argument


def parse_args(sub_parser):
    subparser = sub_parser.add_parser(
        "get-certificate", help="Get the certificate arn needed for the services elb"
    )
    subparser.set_defaults(func=get_certificate_args)
    add_namespace_argument(subparser)
    subparser.add_argument(
        "--for-cluster",
        action="store_true",
        dest="for_cluster",
        help="Get the certificate arn for the cluster's un-namespaced domain name",
    )


def get_certificate_args(args):
    get_certificate(args.namespace, for_cluster=args.for_cluster)


def get_certificate(namespace, for_cluster):
    cr = cluster_rules(namespace=namespace)
    return cr.get_certificate_arn(for_cluster=for_cluster)
