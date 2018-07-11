#!/usr/bin/env python3

import argparse
import logging
import colorlog
import json
import pkg_resources

from arg_tools import add_namespace_argument

from command import \
    build, \
    cluster_init, \
    cmd, \
    connect, \
    deploy, \
    environment, \
    get_certificate, \
    namespace_init, \
    publish, \
    refresh, \
    restart, \
    rollback, \
    scale, \
    start, \
    stop, \
    sync_dns, \
    sync_ingress, \
    tail, \
    undeploy

if __name__ == '__main__':

    parser = argparse.ArgumentParser(prog='aladdin', description='Managing kubernetes projects')
    subparsers = parser.add_subparsers(help='aladdin subcommands')
    subcommands = [
        build,
        cluster_init, \
        cmd,
        connect,
        deploy,
        environment,
        get_certificate,
        namespace_init,
        publish,
        refresh,
        restart,
        rollback,
        scale,
        start,
        stop,
        sync_dns,
        sync_ingress,
        tail,
        undeploy
    ]

    # We want to have python help include host commands that run in bash portion of aladdin
    # Create list of tuples going from command name to parse args function
    subcommands = [(subcommand.__name__.split('.')[-1], subcommand.parse_args)
                   for subcommand in subcommands]
    # Add bash commands to above list
    bash_cmd_helps = json.loads(pkg_resources.resource_string(__name__, 'bash_help.json')
                                             .decode('utf-8'))
    for bash_cmd, bash_help in bash_cmd_helps.items():
        # Use default values for bash_cmd and bash_help so they are evaluated at definition time
        # rather than invocation time
        subcommands.append((bash_cmd, lambda sub_parser, bash_cmd=bash_cmd,
                            bash_help=bash_help: sub_parser.add_parser(bash_cmd,
                                                                       help=bash_help['help'])))
    # Alphabetize the list
    subcommands.sort()
    # Add all subcommands in alphabetical order
    for subcommand in subcommands:
        subcommand[1](subparsers)

    # Add optional aladdin wide arguments for better help visibility
    parser.add_argument('--cluster', '-c', help='The cluster name you want to interact with')
    parser.add_argument('--namespace', '-n', help='The namespace name you want to interact with')
    parser.add_argument('--init', action='store_true',
                        help='Force initialization logic')
    parser.add_argument('--dev', action='store_true',
                        help='Mount host\'s aladdin directory onto aladdin container')
    parser.add_argument('--skip-prompts', action='store_true',
                    help='Skip confirmation prompts during command execution')
    parser.add_argument('--non-terminal', action='store_true',
                    help='Run aladdin container without tty')

    # Initialize logging across python
    colorlog.basicConfig(format='%(log_color)s%(levelname)s:%(message)s', level=logging.INFO)
    logging.getLogger('botocore').setLevel(logging.WARNING)

    args = parser.parse_args()
    args.func(args)
