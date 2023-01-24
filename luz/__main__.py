# module imports
from argparse import ArgumentParser
from os import path

# local imports
from .common.logger import ask, error
from .common.utils import get_version
from .compiler.luzbuild import LuzBuild
from .luzgen.modules.modules import assign_module


def main():
    parser = ArgumentParser()


    parser.add_argument('-v', '--version', action='version', version=f'luz v{get_version()}',
                        help='show current version and exit')
    sub_parsers = parser.add_subparsers(help='sub-command help', dest='command')

    # build
    parser_build = sub_parsers.add_parser(
        'build', help='compile a luz project using a LuzBuild')

    # gen
    parser_gen = sub_parsers.add_parser(
        'gen', help='generate a luz project using LuzGen')
    
    parser_gen.add_argument('-t', '--type', action='store', help='the type of project to generate', choices=['tool', 'tweak'], required=False)

    # args
    args = parser.parse_args()

    if args.command is None:
        error('Please specify an operation.')
        exit(1)

    if args.command == 'build':
        if not path.exists('LuzBuild'):
            error('Could not find LuzBuild file in current directory.')
            exit(1)
        LuzBuild().build()
    elif args.command == 'gen':
        if args.type is None:
            args.type = ask('What type of project would you like to generate? (tool/tweak) (enter for "tweak")')
            if args.type == '':
                args.type = 'tweak'
        assign_module(args.type)
    else:
        error(f'Unknown command "{args.command}".')
        exit(1)

    
if __name__ == '__main__':
    main()