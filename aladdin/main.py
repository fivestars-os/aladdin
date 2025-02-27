import argparse
import contextlib
import logging
import sys

import coloredlogs
import verboselogs

from aladdin import env
from aladdin.commands import (
    build,
    build_components,
    cluster_init,
    cmd,
    connect,
    deploy,
    environment,
    get_certificate,
    helm_values,
    namespace_init,
    publish,
    refresh,
    restart,
    rollback,
    scale,
    start,
    stop,
    sync_ingress,
    tail,
    undeploy,
    version,
)
from aladdin.lib.arg_tools import (
    EnvStoreAction,
    EnvStoreTrueAction,
    bash_wrapper,
    get_bash_commands,
)


def cli():
    """
    Entrypoint for aladdin's command line interface
    """

    parser = argparse.ArgumentParser(
        prog="aladdin",
        description="Managing kubernetes projects",
        epilog="If no arguments are specified, the help text is displayed",
        exit_on_error=False,
    )
    subparsers = parser.add_subparsers(help="aladdin commands")
    subcommands = [
        build,
        build_components,
        cluster_init,
        cmd,
        connect,
        deploy,
        environment,
        get_certificate,
        helm_values,
        namespace_init,
        publish,
        refresh,
        restart,
        rollback,
        scale,
        start,
        stop,
        sync_ingress,
        tail,
        undeploy,
        version,
    ]

    # We want to have python help include host commands that run in bash portion of aladdin
    # Create list of tuples going from command name to parse args function
    subcommands = [
        (subcommand.__name__.split(".")[-1], subcommand.parse_args)
        for subcommand in subcommands
    ]
    bash_commands = get_bash_commands()
    bash_command_names = list(map(lambda arg: arg[0], bash_commands))
    subcommands.extend(bash_commands)
    # Alphabetize the list
    subcommands.sort()
    # Add all subcommands in alphabetical order
    for subcommand in map(lambda arg: arg[1], subcommands):
        subcommand(subparsers)

    # Add optional aladdin wide arguments for better help visibility
    parser.add_argument(
        "--cluster",
        "-c",
        help="The cluster name you want to interact with",
        dest="CLUSTER_CODE",
        default="LOCAL",
        action=EnvStoreAction,
    )
    parser.add_argument(
        "--namespace",
        "-n",
        help="The namespace name you want to interact with",
        dest="namespace",
        default="default",
        action=EnvStoreAction,
    )
    parser.add_argument(
        "-i",
        "--init",
        help="Force initialization logic",
        dest="INIT",
        default=False,
        action=EnvStoreTrueAction,
    )
    parser.add_argument(
        "--skip-prompts",
        help="Skip confirmation prompts during command execution",
        dest="SKIP_PROMPTS",
        default=False,
        action=EnvStoreTrueAction,
    )

    # Initialize logging across python
    verboselogs.install()
    coloredlogs.install(
        level=logging.INFO,
        fmt="%(levelname)s: %(message)s",
        level_styles=dict(
            spam=dict(color="green", faint=True),
            debug=dict(color="black", bold=True),
            verbose=dict(color="blue"),
            info=dict(color="white"),
            notice=dict(color="magenta"),
            warning=dict(color="yellow"),
            success=dict(color="green", bold=True),
            error=dict(color="red"),
            critical=dict(color="red", bold=True),
        ),
        field_styles=dict(
            asctime=dict(color="green"),
            hostname=dict(color="magenta"),
            levelname=dict(color="white"),
            name=dict(color="white", bold=True),
            programname=dict(color="cyan"),
            username=dict(color="yellow"),
        ),
    )
    logging.getLogger("botocore").setLevel(logging.WARNING)

    if not sys.argv[1:] or sys.argv[1] in ["-h", "--help"]:
        return parser.print_help()

    cmd_args = list(filter(lambda arg: not arg.startswith("-"), sys.argv[1:]))
    command = cmd_args[0] if cmd_args else None

    # ordering here is important
    # don't try to set config_path if the user is trying
    # to configure the aladdin config
    if command != "config" and not env.set_config_path():
        return sys.exit(1)

    with contextlib.suppress(argparse.ArgumentError):
        # loads up arguments and stores them as env variables
        # fails if the command is bash or plugin, but we still
        # want the env variables to get configured
        parser.parse_known_args()
    env.configure_env()

    # if it's not a command we know about it might be a plugin
    # currently the bash scripts handle plugins
    if not command or command not in subparsers._name_parser_map:
        return bash_wrapper()

    if command and command in bash_command_names:
        return bash_wrapper()

    args = parser.parse_args()
    args.func(args)
