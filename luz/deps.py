# module imports
from os import environ, mkdir, path, system
from subprocess import check_output, DEVNULL

# local imports
from .logger import log_stdout, error, remove_log_stdout
from .utils import cmd_in_path, setup_luz_dir


def get_luz_storage() -> str:
    """Gets the Luz storage directory."""
    if not path.exists(f'{environ.get("HOME")}/.luz'):
        log_stdout('Creating Luz storage directory...')
        mkdir(f'{environ.get("HOME")}/.luz')
        remove_log_stdout('Creating Luz storage directory...')
    return f'{environ.get("HOME")}/.luz'


def logos(files: list) -> list:
    """Use logos on the specified files.
    
    :param list files: The files to use logos on.
    :return: The list of logos'd files.
    """
    # storage dir
    dir = setup_luz_dir()
    # logos dir
    logos = clone_logos()
    # logos executable
    logos_exec = f'{logos}/bin/logos.pl'
    # new files
    new_files = []

    for file in files:
        # declare output var
        output = f'{dir}/logos-processed/{file.split("/")[-1]}'
        # match to case
        file_formatted = file.split('/')[-1].split('.')[-1]
        if file_formatted == 'x':
            log_stdout(f'Processing {file} with Logos...')
            system(f'{logos_exec} {file} > {output}.m')
            new_files.append(f'{output}.m')
            remove_log_stdout(f'Processing {file} with Logos...')
        elif file_formatted == 'xm':
            log_stdout(f'Processing {file} with Logos...')
            system(f'{logos_exec} {file} > {output}.mm')
            new_files.append(f'{output}.mm')
            remove_log_stdout(f'Processing {file} with Logos...')
        else:
            new_files.append(file)

    # return files
    return new_files


def clone_logos(update: bool=False) -> str:
    """Clones logos.
    
    :return: Path to logos dir
    """
    logos_url = 'https://github.com/LuzProject/logos'
    git = cmd_in_path('git')
    storage = get_luz_storage()
    # if git doesnt exist, exit
    if git is None:
        error('Git is needed in order to use Luz.')
        exit(0)
    # if it doesn't exist, clone logos
    if not path.exists(f'{storage}/logos'):
        log_stdout('Cloning logos...')
        check_output(f'{git} clone {logos_url} {storage}/logos --recursive'.split(' '), stdin=DEVNULL, stderr=DEVNULL)
        remove_log_stdout('Cloning logos...')
    # update
    if update:
        log_stdout('Updating logos...')
        check_output(f'cd {storage}/logos && {git} pull'.split(' '), stdin=DEVNULL, stderr=DEVNULL)
        remove_log_stdout('Updating logos...')
    # return path
    return f'{storage}/logos'


def clone_libraries(update: bool = False) -> str:
    """Clones the default Theos libraries.
    
    :return: Path to libraries dir
    """
    libraries_url = '--branch rootless https://github.com/elihwyma/lib'
    git = cmd_in_path('git')
    storage = get_luz_storage()
    # if git doesnt exist, exit
    if git is None:
        error('Git is needed in order to use Luz.')
        exit(0)
    # if it doesn't exist, clone logos
    if not path.exists(f'{storage}/lib'):
        log_stdout('Cloning libraries...')
        check_output(f'{git} clone {libraries_url} {storage}/lib --recursive'.split(' '), stdin=DEVNULL, stderr=DEVNULL)
        remove_log_stdout('Cloning libraries...')
    # update
    if update:
        log_stdout('Updating libraries...')
        check_output(
            f'cd {storage}/lib && {git} pull'.split(' '), stdin=DEVNULL, stderr=DEVNULL)
        remove_log_stdout('Updating libraries...')
    # return path
    return f'{storage}/lib'


def clone_headers(update: bool = False) -> str:
    """Clones the default Theos headers.
    
    :return: Path to headers dir
    """
    headers_url = 'https://github.com/theos/headers'
    git = cmd_in_path('git')
    storage = get_luz_storage()
    # if git doesnt exist, exit
    if git is None:
        error('Git is needed in order to use Luz.')
        exit(0)
    # if it doesn't exist, clone logos
    if not path.exists(f'{storage}/headers'):
        log_stdout('Cloning headers...')
        check_output(f'{git} clone {headers_url} {storage}/headers --recursive'.split(' '),
                     stdin=DEVNULL, stderr=DEVNULL)
        remove_log_stdout('Cloning headers...')
    # update
    if update:
        log_stdout('Updating headers...')
        check_output(
            f'cd {storage}/headers && {git} pull'.split(' '), stdin=DEVNULL, stderr=DEVNULL)
        remove_log_stdout('Updating headers...')
    # return path
    return f'{storage}/headers'
