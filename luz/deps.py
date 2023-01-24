# module imports
from os import environ, mkdir, system
from subprocess import check_output, DEVNULL

# local imports
from .logger import log_stdout, error, remove_log_stdout
from .utils import cmd_in_path, exists, setup_luz_dir


def clone_logos(module, update: bool=False) -> str:
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
    # if it doesn't exist, clone logos
    if not exists(f'{storage}/logos'):
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


def clone_libraries(module, update: bool = False) -> str:
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
    # if it doesn't exist, clone logos
    if not exists(f'{storage}/lib'):
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


def clone_headers(module, update: bool = False) -> str:
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
    # if it doesn't exist, clone logos
    if not exists(f'{storage}/headers'):
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
        output = f'{dir}/logos-processed/{file.split("/")[-1]}'
        # match to case
        file_formatted = file.split('/')[-1].split('.')[-1]
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
