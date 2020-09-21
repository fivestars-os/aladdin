from aladdin.commands.build_components import __main__


def parse_args(sub_parser):
    subparser = sub_parser.add_parser(
        "build-components", help=__main__.__doc__
    )
    subparser.set_defaults(func=lambda args: __main__.main())
