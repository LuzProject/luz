# module imports
from hashlib import md5
from os import environ, getcwd, mkdir
from pathlib import Path
from pkg_resources import get_distribution
from shutil import which
from typing import Union


def resolve_path(path: str) -> Union[Path, list]:
    """Resolve a Path from a String."""
    # format env vars in path
    if "$" in str(path):
        path = format_path(path)
    # get path
    p = Path(path).expanduser()
    # handle globbing
    if "*" in str(path):
        p = Path(path)
        parts = p.parts[1:] if p.is_absolute() else p.parts
        return list(Path(p.root).expanduser().glob(str(Path("").joinpath(*parts))))
    # return path
    return p


def chained_dict_get(dictionary, key: str):
    """Get a value nested in a dictionary by its nested path.

    :param dict dictionary: Dictionary to operate on.
    :param str key: The key to get.
    :return: The value of the key.
    """
    value_path = key.split(".")
    dict_chain = dictionary
    while value_path:
        try:
            dict_chain = dict_chain.get(value_path.pop(0))
        except AttributeError:
            return None
    return dict_chain


def get_from_default(luzbuild, key):
    """Get the specified value from the default config file.

    :param LuzBuild luzbuild: The LuzBuild class.
    :param str key: The key to get.
    :return: The value of the key.
    """
    return chained_dict_get(luzbuild.defaults, key)


def get_from_luzbuild(luzbuild, key):
    """Get the specified value from the LuzBuild config file.

    :param LuzBuild luzbuild: The LuzBuild class.
    :param str key: The key to get.
    :return: The value of the key.
    """
    return chained_dict_get(luzbuild.luzbuild, key)


def get_from_cfg(luzbuild, key, default_look_path: str = None):
    """Get the specified value from either the LuzBuild or the default config file.

    :param LuzBuild luzbuild: The LuzBuild class.
    :param str key: The key to get.
    :param str default_look_path: The path to look for in the default config file. Defaults to the value of `key`.
    :return: The value of the key."""
    value = get_from_luzbuild(luzbuild, key)
    if value is None:
        if default_look_path is not None:
            value = get_from_default(luzbuild, default_look_path)
        else:
            value = get_from_default(luzbuild, key)
    return value


def format_path(file: str) -> str:
    """Format a path that contains environment variables.

    :param str file: Path to format.
    :return: The formatted path.
    """
    new_file = ""
    for f in file.split("/"):
        if f.startswith("$"):
            new_file += environ.get(f[1:]) + "/"
        else:
            new_file += f + "/"
    return new_file


def get_hash(filepath: str):
    """Gets the hash of a specified file.

    :param str filepath: The path to the file.
    :return: The hash of the file.
    """
    md5sum = md5()
    with open(filepath, "rb") as source:
        block = source.read(2**16)
        while len(block) != 0:
            md5sum.update(block)
            block = source.read(2**16)
    return md5sum.hexdigest()


def setup_luz_dir() -> Path:
    """Setup the tmp directory."""
    luz_dir = resolve_path(f"{getcwd()}/.luz")
    if not luz_dir.exists():
        mkdir(luz_dir)

    return luz_dir


def cmd_in_path(cmd: str) -> Union[None, Path]:
    """Check if a command is in the path.

    :param str cmd: The command to check.
    :return: The path to the command, or None if it's not in the path."""
    path = which(cmd)

    if path is None:
        return None

    return resolve_path(path)


def get_luz_storage() -> str:
    """Gets the Luz storage directory."""
    storage_dir = resolve_path("$HOME/.luz")
    if not storage_dir.exists():
        mkdir(storage_dir)
    return storage_dir


def get_version() -> str:
    return get_distribution(__package__.split(".")[0]).version
