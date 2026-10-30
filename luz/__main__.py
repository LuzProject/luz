# Copyright (c) 2026 Jaidan Arenas
"""Main entry point for Luz."""

# module imports
from argparse import ArgumentParser, SUPPRESS
import sys

# local imports
from .config.luz import Luz
from .config.verify import Verify
from .common.logger import ask, error
from .common.utils import get_version, resolve_path
from .common.update import update_luz
from .luzgen.assign import assign_module


def main():
    """Main Luz function."""
    parser = ArgumentParser()

    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"luz v{get_version()}",
        help="show current version and exit",
    )
    sub_parsers = parser.add_subparsers(help="sub-command help", dest="command")

    # build
    parser_build = sub_parsers.add_parser("build", help="compile a luz project using luz.py")
    parser_build.add_argument(
        "-c",
        "--clean",
        action="store_true",
        help="clean the project before building",
        required=False,
    )

    parser_build.add_argument("-m", "--meta", action="append", nargs="+", help="meta configuration (-m {key}={value})")
    parser_build.add_argument("-p", "--path", action="store", help="path to the project to build")
    parser_build.add_argument("-i", "--install", action="store_true", help="install the project after building it")
    parser_build.add_argument("-f", "--funny-time", action="store_true", help=SUPPRESS)

    # verify
    parser_verify = sub_parsers.add_parser("verify", help="verify the format of luz.py")

    parser_verify.add_argument("-p", "--path", action="store", help="path to the project to verify")

    # gen
    parser_gen = sub_parsers.add_parser("gen", help="generate a luz project using LuzGen")
    parser_gen.add_argument(
        "-t",
        "--type",
        action="store",
        help="the type of project to generate",
        choices=["tool", "tweak", "preferences", "prefs"],
        required=False,
    )

    # update
    parser_update = sub_parsers.add_parser("update", help="update the installed Luz command")
    parser_update.add_argument(
        "-r",
        "--ref",
        default="main",
        help="GitHub branch, tag, or commit to install (default: main)",
    )
    parser_update.add_argument(
        "--no-vendors",
        action="store_true",
        help="do not update vendored headers, libraries, and pyLogos",
    )

    # args
    args = parser.parse_args()

    if args.command is None:
        error("No command specified. Showing help message.")
        parser.print_help()
        sys.exit(1)

    try:
        if args.command == "build":
            if args.path is not None:
                args.path = resolve_path(args.path)
            else:
                args.path = resolve_path("./")
            luzbuild_path = f"{args.path}/luzconf.py"
            if not resolve_path(luzbuild_path).exists():
                error("Could not find build file.")
                sys.exit(1)
            luz = Luz(luzbuild_path, args=args)
            luz.build_project()
        elif args.command == "verify":
            if args.path is not None:
                args.path = resolve_path(args.path)
            else:
                args.path = resolve_path("./")
            luzbuild_path = f"{args.path}/luzconf.py"
            if not resolve_path(luzbuild_path).exists():
                error("Could not find build file.")
                sys.exit(1)
            luz = Verify(luzbuild_path)
        elif args.command == "gen":
            if args.type is None:
                args.type = ask('What type of project would you like to generate? (tool/tweak/preferences) (enter for "tweak")')
                if args.type == "":
                    args.type = "tweak"
            assign_module(args.type)
        elif args.command == "update":
            update_luz(ref=args.ref, update_vendors=not args.no_vendors)
        else:
            error(f'Unknown command "{args.command}".')
            sys.exit(1)
    except Exception as err:
        error(err)
        sys.exit(1)


if __name__ == "__main__":
    main()
