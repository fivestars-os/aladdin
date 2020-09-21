import logging

from aladdin.arg_tools import add_namespace_argument
from aladdin.lib.k8s.kubernetes import Kubernetes


def parse_args(sub_parser):
    subparser = sub_parser.add_parser("refresh", help="Delete pods which match app to reload them")
    add_namespace_argument(subparser)
    subparser.add_argument("apps", help="which pods to restart", nargs="+")
    subparser.set_defaults(func=refresh_args)


def refresh_args(args):
    refresh(args.apps, args.namespace)


def refresh(apps, namespace=None):
    k = Kubernetes(namespace=namespace)
    for app in apps:
        logging.info(f"Refreshing deployment {app}")
        k.rolling_update_no_change(app)
