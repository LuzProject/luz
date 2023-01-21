# module imports
from hashlib import md5
from os import getcwd, mkdir, path
from shutil import which
from typing import Union


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
    if not path.exists(dir):
        mkdir(dir)

    return dir


def cmd_in_path(cmd: str) -> Union[None, str]:
	'''Check if command is in PATH'''
	path = which(cmd)

	if path is None:
		return None

	return path
