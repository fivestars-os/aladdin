import argparse
import logging
import subprocess
import sys

from jmespath import search

from arg_tools import add_namespace_argument
from libs.k8s.kubernetes import Kubernetes
from project.project_conf import ProjectConf


def parse_args(sub_parser):
    subparser = sub_parser.add_parser(
        "cmd", help="Run commands on specifc project via its commands pod"
    )
    subparser.add_argument(
        "app_name", type=str, metavar="app_name", help="app to run commands against"
    )
    subparser.add_argument(
        "command_args",
        type=str,
        metavar="comm_args",
        help="command and its args",
        nargs=argparse.REMAINDER,
    )
    add_namespace_argument(subparser)
    subparser.set_defaults(func=cmd_args)


def cmd_args(args):
    cmd(args.app_name, args.command_args, args.namespace)


def cmd(app_name, command_args, namespace=None):
    k = Kubernetes(namespace=namespace)
    pod_name = k.get_pod_name("%s-commands" % app_name)
    logging.info("Command output below...")

    pc = ProjectConf()
    cmd_config = search("cmd", pc.commands_config)

    if search("version", cmd_config) == 2:
        # In commands-base 2.0.0, we moved the commands.py script to /usr/local/bin/aladdin_cmd
        # and made it executable. It's expected that the implementer will provide a she-bang line to
        # indicate which interpreter to use (or none at all if they are using a compiled executable)
        k.kub_exec(pod_name, "%s-commands" % app_name, "/usr/local/bin/aladdin_cmd", *command_args)
    else:

        logging.warning(
            "commands-base:1.0.0 is deprecated."
            " Update your commands images to commands-base:2.0.0"
            " and set commands.cmd.version=2 in your lamp.json file."
        )

        try:
            # See if the commands container uses python3
            executable = (
                k.kub_exec(
                    pod_name, "%s-commands" % app_name, "which", "python3", return_output=True
                )
                .decode(sys.stdout.encoding)
                .strip()
            )
        except subprocess.CalledProcessError:
            # If not, we assume it uses python
            executable = "python"

        k.kub_exec(pod_name, "%s-commands" % app_name, executable, "command.py", *command_args)
