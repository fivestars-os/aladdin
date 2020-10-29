from aladdin.lib.arg_tools import add_namespace_argument, container_command
from aladdin.lib.cluster_rules import cluster_rules
from aladdin.commands import sync_ingress, sync_dns
from aladdin.lib.helm_rules import HelmRules
from aladdin.lib.k8s.helm import Helm


def parse_args(sub_parser):
    subparser = sub_parser.add_parser("rollback", help="Go back to a previous deployment")
    subparser.set_defaults(func=rollback_args)
    add_namespace_argument(subparser)
    subparser.add_argument("project", help="which project to roll back")
    subparser.add_argument(
        "--chart", help="which chart in the project to roll back, defaults to the project name"
    )
    subparser.add_argument(
        "--num-versions", type=int, default=1, help="how many versions to rollback, defaults to 1"
    )
    subparser.add_argument(
        "--helm2",
        action="store_true",
        help="Use helm2 instead of helm3",
    )


def rollback_args(args):
    rollback(args.project, args.num_versions, args.namespace, args.chart, args.helm2)


@container_command
def rollback(project, num_versions, namespace, chart=None, helm2=False):
    helm = Helm(helm2)

    cr = cluster_rules(namespace=namespace)
    hr = HelmRules(cr, chart or project)

    helm.rollback_relative(hr, num_versions, namespace)

    sync_ingress.sync_ingress(namespace)
    sync_dns.sync_dns(namespace)
