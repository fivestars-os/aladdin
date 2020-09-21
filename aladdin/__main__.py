import argparse
import os
import subprocess
import sys

import aladdin

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))


def _aladdin_bash():
    _, *args = sys.argv
    handler = os.path.join(PROJECT_ROOT, "aladdin.sh")
    subprocess.call([handler, *args])


def version(parser: argparse.ArgumentParser):
    parser.set_defaults(
        handler=lambda **kwards: print("v" + aladdin.__version__)
    )


def main():
    parser = argparse.ArgumentParser(prog="aladdin", add_help=False)
    parser.set_defaults(handler=_aladdin_bash)

    subparsers = parser.add_subparsers()
    version(subparsers.add_parser("version"))

    subcommands = list(filter(lambda arg: not arg.startswith("-"), sys.argv[1:]))
    if not subcommands or subcommands[0] not in subparsers._name_parser_map:
        return _aladdin_bash()

    kwargs = vars(parser.parse_args())
    handler = kwargs.pop("handler")
    handler(**kwargs)
