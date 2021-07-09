import argparse

from aladdin.lib.project_conf import ProjectConf
from aladdin.lib.arg_tools import container_command
from aladdin.lib.k8s.k3d import K3d


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
    k3d = K3d()
    pc = ProjectConf()
    pc.build_docker(env={"HASH": tag}, build_args=build_args)
    images = pc.get_docker_images()
    if images:
        k3d.import_images([f"{image}:{tag}" for image in images])
