from aladdin.cluster_rules import cluster_rules
from aladdin.arg_tools import add_namespace_argument, container_command


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


@container_command
def get_certificate(namespace, for_cluster):
    cr = cluster_rules(namespace=namespace)
    return cr.cluster_certificate_arn if for_cluster else cr.service_certificate_arn
