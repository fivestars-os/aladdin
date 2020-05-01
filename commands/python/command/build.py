#!/usr/bin/env python3
import argparse

from project.project_conf import ProjectConf


def parse_args(sub_parser):
    subparser = sub_parser.add_parser(
        "build", help="Build a project's docker images for local development"
    )
    subparser.add_argument("build_args", nargs=argparse.REMAINDER)
    subparser.set_defaults(func=build_args)


def build_args(args):
    build(args.build_args)


def build(build_args):
    pc = ProjectConf()
    pc.build_docker(env={"HASH": "local"}, build_args=build_args)
