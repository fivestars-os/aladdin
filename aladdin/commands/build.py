import argparse

from aladdin.lib.arg_tools import container_command
from aladdin.lib.project_conf import ProjectConf


def parse_args(sub_parser):
    subparser = sub_parser.add_parser(
        "build", help="Build a project's docker images for local development"
    )
    subparser.add_argument("build_args", nargs=argparse.REMAINDER)
    subparser.set_defaults(func=build_args)


def build_args(args):
    build(args.build_args)


@container_command
def build(build_args):
    tag = "local"
    pc = ProjectConf()
    pc.build_docker(env={"HASH": tag}, build_args=build_args)
