from aladdin.lib.arg_tools import add_namespace_argument, container_command
from aladdin.lib.cluster_rules import ClusterRules
from aladdin.commands import sync_ingress, sync_dns
from aladdin.lib.helm_rules import HelmRules
from aladdin.lib.k8s.helm import Helm


def parse_args(sub_parser):
    subparser = sub_parser.add_parser(
        "undeploy", help="Remove the helm chart in non local environments"
    )
    subparser.set_defaults(func=undeploy_args)
    add_namespace_argument(subparser)
    subparser.add_argument("project", help="which project to undeploy")
    subparser.add_argument(
        "--chart",
        help="which chart in the project to undeploy, defaults to the project name"
    )


def undeploy_args(args):
    undeploy(args.project, args.namespace, args.chart)


@container_command
def undeploy(project, namespace, chart=None):
    helm = Helm()

    cr = ClusterRules(namespace=namespace)
    hr = HelmRules(cr, chart or project)

    helm.stop(hr, namespace)

    sync_ingress.sync_ingress(namespace)
    sync_dns.sync_dns(namespace)
