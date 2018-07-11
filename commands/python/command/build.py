#!/usr/bin/env python3
from project.project_conf import ProjectConf


def parse_args(sub_parser):
    subparser = sub_parser.add_parser('build',
                                      help='Build a project\'s docker images for local development')
    subparser.set_defaults(func=build_args)


def build_args(args):
    build()


def build():
    pc = ProjectConf()
    pc.build_docker(env={'HASH':'local'})
