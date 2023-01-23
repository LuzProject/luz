# module imports
from hashlib import md5
from os import environ, getcwd, mkdir, path
from pathlib import Path
from pkg_resources import get_distribution
from shutil import which
from subprocess import getoutput
from typing import Union


def chained_dict_get(dictionary, key: str):
    """Get a value nested in a dictionary by its nested path."""
    value_path = key.split('.')
    dict_chain = dictionary
    while value_path:
        try:
            dict_chain = dict_chain.get(value_path.pop(0))
        except AttributeError:
            return None
    return dict_chain


def get_from_default(luzbuild, key): return chained_dict_get(luzbuild.defaults, key)


def get_from_luzbuild(luzbuild, key): return chained_dict_get(luzbuild.luzbuild, key)


def get_from_cfg(luzbuild, key, default_look_path: str = None):
    """Get the specified value from either the LuzBuild or the default config file."""
    value = get_from_luzbuild(luzbuild, key)
    if value is None:
        if default_look_path is not None:
            value = get_from_default(luzbuild, default_look_path)
        else:
            value = get_from_default(luzbuild, key)
    return value


def format_path(file: str) -> str:
    new_file = ''
    for f in file.split('/'):
        if f.startswith('$'):
            new_file += environ.get(f[1:]) + '/'
        else:
            new_file += f + '/'
    return new_file


def exists(file: str) -> bool: return path.exists(format_path(file))


def get_hash(filepath: str):
    """Gets the hash of a specified file.
    
    :param str filepath: The path to the file.
    :return: The hash of the file.
    """
    md5sum = md5()
    with open(filepath, 'rb') as source:
        block = source.read(2**16)
        while len(block) != 0:
            md5sum.update(block)
            block = source.read(2**16)
    return md5sum.hexdigest()


def setup_luz_dir() -> str:
    """Setup the tmp directory."""
    dir = getcwd() + '/.luz'
    if not exists(dir):
        mkdir(dir)

    return dir


def cmd_in_path(cmd: str) -> Union[None, str]:
	'''Check if command is in PATH'''
	path = which(cmd)

	if path is None:
		return None

	return path


def get_version() -> str:
	# Check if running from a git repository,
	# then, construct version in the following format: version-branch-hash
	if Path('.git').exists():
		return f'{get_distribution(__package__).version}-{getoutput("git rev-parse --abbrev-ref HEAD")}-{getoutput("git rev-parse --short HEAD")}'
	else:
		return get_distribution(__package__).version