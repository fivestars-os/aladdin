import functools
import json
import os
import subprocess
import sys
import pkg_resources

from aladdin.config import PROJECT_ROOT
from aladdin.lib import in_aladdin_container


def add_namespace_argument(arg_parser):
    namespace_def = os.getenv("NAMESPACE", "default")
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
        if not in_aladdin_container():
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
