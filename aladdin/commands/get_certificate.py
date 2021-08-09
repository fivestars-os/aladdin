import time

from aladdin.lib.cluster_rules import cluster_rules
from aladdin.lib.arg_tools import add_namespace_argument, container_command, expand_namespace


def parse_args(sub_parser):
    subparser = sub_parser.add_parser(
        "get-certificate", help="Get the certificate arn needed for the services elb"
    )
    subparser.set_defaults(func=get_certificate)
    add_namespace_argument(subparser)
    subparser.add_argument(
        "--for-cluster",
        action="store_true",
        dest="for_cluster",
        help="Get the certificate arn for the cluster's un-namespaced domain name",
    )
    subparser.add_argument(
        "--wait",
        action="store_true",
        dest="wait",
        help="Wait for certificate to be ready",
    )


@container_command
@expand_namespace
def get_certificate(namespace: str, for_cluster: bool = False, wait: bool = False):
    cr = cluster_rules(namespace=namespace)
    cert = None
    while not cert:
        cert = cr.cluster_certificate_arn if for_cluster else cr.service_certificate_arn
        if not wait:
            return cert
        if not cert:
            time.sleep(10)
    return cert
