# module imports
from argparse import ArgumentParser

# local imports
from .config.luz import Luz
from .common.logger import ask, error
from .common.utils import get_version, resolve_path
from .luzgen.modules.modules import assign_module


def main():
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
    parser_build = sub_parsers.add_parser("build", help="compile a luz project using a LuzBuild")
    parser_build.add_argument(
        "-c",
        "--clean",
        action="store_true",
        help="clean the project before building",
        required=False,
    )

    parser_build.add_argument("-m", "--meta", action="append", nargs="+", help="meta configuration (-m {key}={value})")
    parser_build.add_argument("-p", "--path", action="store", help="path to the project to build")

    # gen
    parser_gen = sub_parsers.add_parser("gen", help="generate a luz project using LuzGen")
    parser_gen.add_argument(
        "-t",
        "--type",
        action="store",
        help="the type of project to generate",
        choices=["tool", "tweak"],
        required=False,
    )

    # args
    args = parser.parse_args()

    if args.command is None:
        error("Please specify an operation.")
        exit(1)

    try:
        if args.command == "build":
            if args.path is not None:
                args.path = resolve_path(args.path)
            else:
                args.path = resolve_path("./")
            luzbuild_path = f"{args.path}/luz.py"
            if not resolve_path(f"{args.path}/luz.py").exists():
                error("Could not find build file.")
                exit(1)
            elif resolve_path(f"{args.path}/LuzBuild").exists():
                error("LuzBuild has been deprecated. Luz now uses a Python file to build projects. See the docs for more information.")
                exit(1)
            luz = Luz(luzbuild_path, args=args)
            luz.build_project()
        elif args.command == "gen":
            if args.type is None:
                args.type = ask('What type of project would you like to generate? (tool/tweak/preferences) (enter for "tweak")')
                if args.type == "":
                    args.type = "tweak"
            assign_module(args.type)
        else:
            error(f'Unknown command "{args.command}".')
            exit(1)
    except Exception as e:
        error(f"{e}")
        exit(1)


if __name__ == "__main__":
    main()
