# module imports
from argparse import ArgumentParser
from os import path

# local imports
from .logger import Error
from .luzbuild import LuzBuild
from .utils import get_version

def main():
    parser = ArgumentParser()


    parser.add_argument('-v', '--version', action='version', version=f'luz v{get_version()}',
                        help='show current version and exit')
    sub_parsers = parser.add_subparsers(help='sub-command help', dest='command')

    # build
    parser_build = sub_parsers.add_parser(
        'build', help='compile a luz project using a LuzBuild')

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
	else:
		error(f'Unknown command "{args.command}".')
        exit(1)

    
if __name__ == '__main__':
    main()