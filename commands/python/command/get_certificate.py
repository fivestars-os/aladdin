#!/usr/bin/env python3
from cluster_rules import cluster_rules
from arg_tools import add_namespace_argument


def parse_args(sub_parser):
    subparser = sub_parser.add_parser(
        "get-certificate", help="Get the certificate arn needed for the services elb"
    )
    subparser.set_defaults(func=get_certificate_args)
    add_namespace_argument(subparser)


def get_certificate_args(args):
    get_certificate(args.namespace)


def get_certificate(namespace):
    cr = cluster_rules(namespace=namespace)
    return cr.get_certificate_arn()
