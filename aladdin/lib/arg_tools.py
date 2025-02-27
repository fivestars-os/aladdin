import argparse
import functools
import json
import os
import sys
from contextlib import suppress
from inspect import signature

import pkg_resources
from kubernetes import config as kube_config

from aladdin.config import PROJECT_ROOT


def get_current_namespace():
    namespace = os.getenv("HELM_NAMESPACE")

    if not namespace:
        namespace = os.getenv("NAMESPACE")

    if not namespace:
        with suppress(KeyError, kube_config.config_exception.ConfigException):
            _, active_context = kube_config.list_kube_config_contexts()
            namespace = active_context["context"]["namespace"]

    if not namespace:
        namespace = "default"
    return namespace


def add_namespace_argument(arg_parser):
    _current_namespace = get_current_namespace()
    arg_parser.add_argument(
        "--namespace",
        "-n",
        default=_current_namespace,
        dest="namespace",
        action=EnvStoreAction,
        help=f"namespace name, defaults to current: [{_current_namespace}]",
    )


def bash_wrapper():
    _, *args = sys.argv
    handler = PROJECT_ROOT / "aladdin.sh"
    os.environ["PYTHONPATH"] = ":".join(sys.path)
    os.execv(str(handler), ["aladdin.sh", *args])


def container_command(func=None):
    """
    Decorator to wrap aladdin commands that
    need to be run inside the aladdin container
    """

    @functools.wraps(func)
    def _wrapper(*args, **kwargs):
        # using `ALADDIN_CONTAINER` as way to know if we're "in" the aladdin container
        if not os.getenv("ALADDIN_CONTAINER"):
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


HELM_OPTION_PARSER = argparse.ArgumentParser(add_help=False)
HELM_OPTION_PARSER.add_argument(
    "--dry-run",
    "-d",
    action="store_true",
    help="Run the helm as test and don't actually run it",
)
HELM_OPTION_PARSER.add_argument(
    "--force-helm",
    action="store_true",
    help="Have helm force resource update through delete/recreate if needed",
)
HELM_OPTION_PARSER.add_argument(
    "--set-override-values",
    default=[],
    nargs="+",
    help=(
        "override values in the values file. "
        "Syntax: --set-override-values key1=value1 key2=value2 ..."
    ),
)
HELM_OPTION_PARSER.add_argument(
    "--values-file",
    default=[],
    dest="values_files",
    action="append",
    type=str,
    help=(
        "add values file to override chart values. "
        "Syntax: --values-file my-values.yaml ..."
    ),
)

CHART_OPTION_PARSER = argparse.ArgumentParser(add_help=False)
CHART_OPTION_PARSER.add_argument(
    "--chart", help="which chart in the project to use, defaults to the project name"
)

CHARTS_OPTION_PARSER = argparse.ArgumentParser(add_help=False)
CHARTS_OPTION_PARSER.add_argument(
    "--chart",
    action="append",
    dest="charts",
    help=(
        "which chart in the project to use, defaults to all the project charts "
        "(may be specified multiple times)"
    ),
)

COMMON_OPTION_PARSER = argparse.ArgumentParser(add_help=False)


def expand_namespace(func=None):
    """
    Decorator to expand an argparse.Namespace obj into keyworded arguments
    and inject them into a function. It inspects the decorated function and only injects
    arguments included in the function signature (to avoid `TypeError`).
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if len(args) == 1 and isinstance(args[0], argparse.Namespace):
            nmspace = {k.replace("-", "_"): v for (k, v) in vars(args[0]).items()}
            allowed = list(signature(func).parameters.keys())
            return func(**{k: v for (k, v) in nmspace.items() if k in allowed})
        return func(*args, **kwargs)

    if not func:
        return expand_namespace
    return wrapper


class EnvActionMixin:
    def __call__(self, parser, namespace, values, option_string=None):
        super().__call__(parser, namespace, values, option_string)
        value = getattr(namespace, self.dest)
        if isinstance(value, bool):
            value = str(value).lower()
        os.environ[self.dest.upper()] = str(value)


class EnvStoreAction(EnvActionMixin, argparse._StoreAction):
    pass


class EnvStoreTrueAction(EnvActionMixin, argparse._StoreTrueAction):
    pass


add_namespace_argument(COMMON_OPTION_PARSER)
