# module imports
from os import makedirs
from pathlib import Path
from subprocess import getoutput

# local imports
from ..common.logger import log_stdout, remove_log_stdout
from ..common.utils import resolve_path


def clone_logos(module, update: bool = False) -> Path:
    """Clones logos.

    :param Tweak module: The module to use logos on.
    :param bool update: Whether to update logos or not.
    :return: Path to logos dir
    """
    logos_url = "https://github.com/LuzProject/logos"
    storage = module.storage
    # logos path
    logos_path = resolve_path(f"{storage}/vendor/logos")
    # if it doesn't exist, clone logos
    if not logos_path.exists():
        log_stdout("Cloning logos...")
        makedirs(logos_path.parent, exist_ok=True)
        getoutput(f"{module.git} clone {logos_url} {logos_path} --recursive")
        remove_log_stdout("Cloning logos...")
    # update
    if update:
        log_stdout("Updating logos...")
        getoutput(f"cd {logos_path} && {module.git} pull")
        remove_log_stdout("Updating logos...")
    # return path
    return logos_path


def clone_libraries(module, update: bool = False) -> Path:
    """Clones the default Theos libraries.

    :param Module module: The module to clone libraries for
    :param bool update: Whether to update libraries or not.
    :return: Path to libraries dir
    """
    libraries_url = "--branch rootless https://github.com/elihwyma/lib"
    storage = module.storage
    # libraries path
    libraries_path = resolve_path(f"{storage}/vendor/lib")
    # if it doesn't exist, clone logos
    if not libraries_path.exists():
        log_stdout("Cloning libraries...")
        makedirs(libraries_path.parent, exist_ok=True)
        getoutput(f"{module.git} clone {libraries_url} {libraries_path} --recursive")
        remove_log_stdout("Cloning libraries...")
    # update
    if update:
        log_stdout("Updating libraries...")
        getoutput(f"cd {libraries_path} && {module.git} pull")
        remove_log_stdout("Updating libraries...")
    # return path
    return libraries_path


def clone_headers(module, update: bool = False) -> Path:
    """Clones the default Theos headers.

    :param Module module: The module to clone headers for.
    :param bool update: Whether to update headers or not.
    :return: Path to headers dir
    """
    headers_url = "https://github.com/theos/headers"
    storage = module.storage
    # headers path
    headers_path = resolve_path(f"{storage}/vendor/headers")
    # if it doesn't exist, clone logos
    if not headers_path.exists():
        log_stdout("Cloning headers...")
        makedirs(headers_path.parent, exist_ok=True)
        getoutput(f"{module.git} clone {headers_url} {headers_path} --recursive")
        remove_log_stdout("Cloning headers...")
    # update
    if update:
        log_stdout("Updating headers...")
        getoutput(f"cd {headers_path} && {module.git} pull")
        remove_log_stdout("Updating headers...")
    # return path
    return headers_path


def logos(module, files: list) -> list:
    """Use logos on the specified files.

    :param Tweak module: The module to use logos on.
    :param list files: The files to use logos on.
    :return: The list of logos'd files.
    """
    dir = module.dir
    # logos dir
    logos = clone_logos(module)
    # logos executable
    logos_exec = f"{logos}/bin/logos.pl"
    # new files
    new_files = []

    for file in files:
        # declare output var
        output = f'{dir}/logos-processed/{str(file).split("/")[-1]}'
        # match to case
        file_formatted = str(file).split("/")[-1].split(".")[-1]
        if file_formatted == "x":
            log_stdout(f"Processing {file} with Logos...")
            getoutput(f"{logos_exec} {file} > {output}.m")
            new_files.append(
                {
                    "logos": True,
                    "new_path": resolve_path(f"{output}.m"),
                    "old_path": resolve_path(file),
                }
            )
            remove_log_stdout(f"Processing {file} with Logos...")
        elif file_formatted == "xm":
            log_stdout(f"Processing {file} with Logos...")
            getoutput(f"{logos_exec} {file} > {output}.mm")
            new_files.append(
                {
                    "logos": True,
                    "new_path": resolve_path(f"{output}.mm"),
                    "old_path": resolve_path(file),
                }
            )
            remove_log_stdout(f"Processing {file} with Logos...")
        else:
            new_files.append({"logos": False, "path": resolve_path(file)})

    # return files
    return new_files
