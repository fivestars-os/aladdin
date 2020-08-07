#!/usr/bin/env python3
from arg_tools import add_namespace_argument
from command import stop, start


def parse_args(sub_parser):
    subparser = sub_parser.add_parser("restart", help="Remove everything before deploying again")
    subparser.set_defaults(func=restart_args)
    add_namespace_argument(subparser)
    subparser.add_argument(
        "--chart",
        action="append",
        dest="charts",
        help="Only start these charts (may be specified multiple times)",
    )
    subparser.add_argument(
        "--with-mount",
        "-m",
        action="store_true",
        help="Mount user's host's project repo onto container",
    )


def restart_args(args):
    restart(args.namespace, args.charts, args.with_mount)


def restart(namespace, charts, with_mount):
    stop.stop(namespace)
    start.start(namespace, charts, False, with_mount)
