import argparse
import time

from aladdin.lib.cluster_rules import cluster_rules
from aladdin.lib.arg_tools import add_namespace_argument, container_command, expand_namespace


def parse_args(parser):
    subparser: argparse.ArgumentParser = parser.add_parser(
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
        type=int,
        default=0,
        dest="wait",
        help="Seconds to wait for certificate to be ready (use -1 to wait forever)",
    )
    subparser.add_argument(
        "--poll-interval",
        type=int,
        default=10,
        dest="poll_interval",
        help="Seconds to wait between polls to AWS ACM",
    )


@container_command
@expand_namespace
def get_certificate(
    namespace: str,
    for_cluster: bool = False,
    wait: int = 0,
    poll_interval: int = 10
):
    cr = cluster_rules(namespace=namespace)
    cert = None
    timeout_start = time.time()
    while not cert:
        if for_cluster:
            cert = cr.get_cluster_certificate_arn()
        else:
            cert = cr.get_service_certificate_arn()
        if not wait:
            return cert
        if wait > 0 and time.time() - timeout_start > wait:
            return cert
        if not cert:
            time.sleep(poll_interval)
    return cert
