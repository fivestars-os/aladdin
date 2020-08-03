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
        "--global",
        "-g",
        action="store_true",
        dest="get_global",
        help='Get the certificate arn for the cluster\'s "global" namespace',
    )


def get_certificate_args(args):
    get_certificate(args.namespace, get_global=args.get_global)


def get_certificate(namespace, get_global):
    cr = cluster_rules(namespace=namespace)
    return cr.get_certificate_arn(get_global=get_global)
