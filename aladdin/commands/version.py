import logging

import aladdin


def parse_args(parser):
    subparser = parser.add_parser("version", help="Show aladdin version")
    subparser.set_defaults(
        func=lambda args: logging.info("v" + aladdin.__version__)
    )
