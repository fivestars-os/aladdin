#!/usr/bin/env python3
import os


def add_namespace_argument(arg_parser):
    namespace_def = os.getenv("NAMESPACE", "default")
    arg_parser.add_argument(
        "--namespace",
        "-n",
        default=namespace_def,
        help="namespace name, defaults to default current : [{}]".format(namespace_def),
    )
