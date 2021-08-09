import functools
import json
import os
import subprocess
import sys
import pkg_resources
from contextlib import suppress
from inspect import signature

from kubernetes import config as kube_config

from aladdin.config import PROJECT_ROOT


def get_current_namespace():
    namespace = os.getenv("NAMESPACE")

    if not namespace:
        with suppress(KeyError, kube_config.config_exception.ConfigException):
            _, active_context = kube_config.list_kube_config_contexts()
            namespace = active_context["context"]["namespace"]

    if not namespace:
        namespace = "default"
    return namespace


def expand_namespace(func=None):
    """
    Decorator to expand a Namespace obj into keyworded arguments
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if len(args) == 1 and isinstance(args[0], argparse.Namespace):
            nmspace = vars(args[0])
            allowed = list(signature(func).parameters.keys())
            return func(**{k: v for (k, v) in nmspace.items() if k in allowed})
        return func(*args, **kwargs)

    if not func:
        return expand_namespace
    return wrapper

def add_namespace_argument(arg_parser):
    namespace_def = get_current_namespace()
    arg_parser.add_argument(
        "--namespace",
        "-n",
        default=namespace_def,
        help="namespace name, defaults to default current : [{}]".format(namespace_def),
    )


def bash_wrapper():
    _, *args = sys.argv
    handler = os.path.join(PROJECT_ROOT, "aladdin.sh")
    subprocess.run([handler, *args])


def container_command(func=None):
    """
    Decorator to wrap aladdin commands that
    need to be run inside the aladdin container
    """
    @functools.wraps(func)
    def _wrapper(*args, **kwargs):
        # using `CLUSTER_CODE` as tell-tale to know
        # if we're "in" the aladdin container
        if not os.getenv("CLUSTER_CODE"):
            return bash_wrapper()
        return func(*args, **kwargs)
    if not func:
        return container_command
    return _wrapper


def get_bash_commands():
    commands = []
    bash_cmd_helps = json.loads(
        pkg_resources.resource_string("aladdin", "bash_help.json").decode("utf-8")
    )

    for bash_cmd, bash_help in bash_cmd_helps.items():
        # Use default values for bash_cmd and bash_help so they are evaluated at definition time
        # rather than invocation time
        def add_command(parser, cmd=bash_cmd, help_msg=bash_help["help"]):
            sub_parser = parser.add_parser(cmd, help=help_msg)
            sub_parser.set_defaults(func=lambda args: bash_wrapper())
        commands.append((bash_cmd, add_command))
    return commands
