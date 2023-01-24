# module imports
from os import system
from pathlib import Path
from subprocess import check_output, DEVNULL

# local imports
from ..common.logger import log_stdout, error, remove_log_stdout
from ..common.utils import cmd_in_path, resolve_path


def clone_logos(module, update: bool=False) -> Path:
    """Clones logos.
    
    :param Tweak module: The module to use logos on.
    :param bool update: Whether to update logos or not.
    :return: Path to logos dir
    """
    logos_url = 'https://github.com/LuzProject/logos'
    git = cmd_in_path('git')
    storage = module.storage
    # if git doesnt exist, exit
    if git is None:
        error('Git is needed in order to use Luz.')
        exit(0)
    # logos path
    logos_path = resolve_path(f'{storage}/logos')
    # if it doesn't exist, clone logos
    if not logos_path.exists():
        log_stdout('Cloning logos...')
        check_output(f'{git} clone {logos_url} {logos_path} --recursive'.split(' '), stdin=DEVNULL, stderr=DEVNULL)
        remove_log_stdout('Cloning logos...')
    # update
    if update:
        log_stdout('Updating logos...')
        check_output(f'cd {logos_path} && {git} pull'.split(' '), stdin=DEVNULL, stderr=DEVNULL)
        remove_log_stdout('Updating logos...')
    # return path
    return logos_path


def clone_libraries(module, update: bool = False) -> Path:
    """Clones the default Theos libraries.
    
    :param Module module: The module to clone libraries for
    :param bool update: Whether to update libraries or not.
    :return: Path to libraries dir
    """
    libraries_url = '--branch rootless https://github.com/elihwyma/lib'
    git = cmd_in_path('git')
    storage = module.storage
    # if git doesnt exist, exit
    if git is None:
        error('Git is needed in order to use Luz.')
        exit(0)
    # libraries path
    libraries_path = resolve_path(f'{storage}/lib')
    # if it doesn't exist, clone logos
    if not libraries_path.exists():
        log_stdout('Cloning libraries...')
        check_output(f'{git} clone {libraries_url} {libraries_path} --recursive'.split(' '), stdin=DEVNULL, stderr=DEVNULL)
        remove_log_stdout('Cloning libraries...')
    # update
    if update:
        log_stdout('Updating libraries...')
        check_output(
            f'cd {libraries_path} && {git} pull'.split(' '), stdin=DEVNULL, stderr=DEVNULL)
        remove_log_stdout('Updating libraries...')
    # return path
    return libraries_path


def clone_headers(module, update: bool = False) -> Path:
    """Clones the default Theos headers.
    
    :param Module module: The module to clone headers for.
    :param bool update: Whether to update headers or not.
    :return: Path to headers dir
    """
    headers_url = 'https://github.com/theos/headers'
    git = cmd_in_path('git')
    storage = module.storage
    # if git doesnt exist, exit
    if git is None:
        error('Git is needed in order to use Luz.')
        exit(0)
    # headers path
    headers_path = resolve_path(f'{storage}/headers')
    # if it doesn't exist, clone logos
    if not headers_path.exists():
        log_stdout('Cloning headers...')
        check_output(f'{git} clone {headers_url} {headers_path} --recursive'.split(' '),
                     stdin=DEVNULL, stderr=DEVNULL)
        remove_log_stdout('Cloning headers...')
    # update
    if update:
        log_stdout('Updating headers...')
        check_output(
            f'cd {headers_path} && {git} pull'.split(' '), stdin=DEVNULL, stderr=DEVNULL)
        remove_log_stdout('Updating headers...')
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
    logos_exec = f'{logos}/bin/logos.pl'
    # new files
    new_files = []

    for file in files:
        # declare output var
        output = f'{dir}/logos-processed/{str(file).split("/")[-1]}'
        # match to case
        file_formatted = str(file).split('/')[-1].split('.')[-1]
        if file_formatted == 'x':
            log_stdout(f'Processing {file} with Logos...')
            system(f'{logos_exec} {file} > {output}.m')
            new_files.append(
                {'logos': True, 'new_path': f'{output}.m', 'old_path': file})
            remove_log_stdout(f'Processing {file} with Logos...')
        elif file_formatted == 'xm':
            log_stdout(f'Processing {file} with Logos...')
            system(f'{logos_exec} {file} > {output}.mm')
            new_files.append(
                {'logos': True, 'new_path': f'{output}.mm', 'old_path': file})
            remove_log_stdout(f'Processing {file} with Logos...')
        else:
            new_files.append({'logos': False, 'path': file})

    # return files
    return new_files
