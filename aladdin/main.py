import argparse
import logging
import sys

import verboselogs
import coloredlogs

from aladdin import env
from aladdin.lib.arg_tools import get_bash_commands, bash_wrapper
from aladdin.commands import (
    build,
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
    version
)


def cli():
    """
    Entrypoint for aladdin's command line interface
    """

    parser = argparse.ArgumentParser(
        prog="aladdin",
        description="Managing kubernetes projects",
        epilog="If no arguments are specified, the help text is displayed",
    )
    subparsers = parser.add_subparsers(help="aladdin commands")
    subcommands = [
        build,
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
        (subcommand.__name__.split(".")[-1], subcommand.parse_args) for subcommand in subcommands
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
    parser.add_argument("--cluster", "-c", help="The cluster name you want to interact with")
    parser.add_argument("--namespace", "-n", help="The namespace name you want to interact with")
    parser.add_argument("-i", "--init", action="store_true", help="Force initialization logic")
    parser.add_argument("--image", help="Use the specified aladdin image (if building it yourself)")
    parser.add_argument(
        "--skip-prompts",
        action="store_true",
        help="Skip confirmation prompts during command execution",
    )
    parser.add_argument(
        "--non-terminal", action="store_true", help="Run aladdin container without tty"
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
    env.configure_env()

    # if it's not a command we know about it might be a plugin
    # currently the bash scripts handle plugins
    if not command or command not in subparsers._name_parser_map:
        return bash_wrapper()

    if command and command in bash_command_names:
        return bash_wrapper()

    args = parser.parse_args()
    args.func(args)
