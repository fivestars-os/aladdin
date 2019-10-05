import argparse
import logging
import subprocess
import sys

from arg_tools import add_namespace_argument
from libs.k8s.kubernetes import Kubernetes


def parse_args(sub_parser):
    subparser = sub_parser.add_parser('cmd',
                                      help='Run commands on specifc project via its commands pod')
    subparser.add_argument('app_name', type=str, metavar='app_name',
                           help='app to run commands against')
    subparser.add_argument('command_args', type=str, metavar='comm_args',
                           help='command and its args', nargs=argparse.REMAINDER)
    add_namespace_argument(subparser)
    subparser.set_defaults(func=cmd_args)


def cmd_args(args):
    cmd(args.app_name, args.command_args, args.namespace)


def cmd(app_name, command_args, namespace=None):
    k = Kubernetes(namespace=namespace)
    pod_name = k.get_pod_name("%s-commands" % app_name)
    logging.info("Command output below...")

    if not uses_new_cmd(k, pod_name, app_name):
        try:
            # See if the commands container uses python3
            executable = k.kub_exec(pod_name, "%s-commands" % app_name, 'which', 'python3',
                                    return_output=True).decode(sys.stdout.encoding).strip()
        except subprocess.CalledProcessError:
            # If not, we assume it uses python
            executable = 'python'
        k.kub_exec(pod_name, "%s-commands" % app_name, executable, 'command.py', *command_args)
    else:
        k.kub_exec(pod_name, "%s-commands" % app_name, 'aladdin-command', *command_args)


def uses_new_cmd(k, pod_name, app_name):
    try:
        k.kub_exec(pod_name, "%s-commands" % app_name, 'which', 'aladdin-command',
                   return_output=True).decode(sys.stdout.encoding).strip()
    except subprocess.CalledProcessError:
        return False
    return True
