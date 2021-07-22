from aladdin.lib.arg_tools import add_namespace_argument, container_command
from aladdin.commands import stop, start


def parse_args(sub_parser):
    subparser = sub_parser.add_parser("restart", help="Remove everything before deploying again")
    subparser.set_defaults(func=restart_args)
    add_namespace_argument(subparser)
    subparser.add_argument(
        "--chart",
        action="append",
        dest="charts",
        help="Start only these charts (may be specified multiple times)",
    )


def restart_args(args):
    restart(args.namespace, args.charts)


@container_command
def restart(namespace, charts):
    stop.stop(namespace, charts)
    start.start(namespace, charts, False)
