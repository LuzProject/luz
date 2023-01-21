# module imports
from os import path
from pyclang import CCompiler
from shutil import rmtree
from subprocess import getoutput

# local imports
from ..deps import clone_headers, clone_libraries
from ..logger import error, log_stdout, remove_log_stdout
from ..utils import cmd_in_path, setup_luz_dir


def get_safe(module: dict, key: str, default: str = None) -> str:
    """Gets a key from a dict safely.
    
    :param dict module: The dict to get the key from.
    :param str key: The key to get.
    :param str default: The default value to return if the key is not found.
    :return: The value of the key.
    """
    return module.get(key) if module.get(key) is not None else default


class Module:
    def __init__(self, module: dict, key: str, compiler: CCompiler, control: str):
        # declare raw module
        self.__raw_module = module

        # raw control
        self.__raw_control = control

        # type
        self.type = get_safe(module, 'type', 'tweak')

        # process
        self.filter = get_safe(module, 'filter', {'executables': ['SpringBoard']})

        # compiler
        self.compiler = compiler

        # name
        self.name = key

        # use arc
        self.arc = bool(
            get_safe(module, 'arc', True if self.type == 'tweak' else False))

        # only compile changes
        self.only_compile_changed = get_safe(
            module, 'only_compile_changed', False)

        # ensure files are defined
        if module.get('files') is None:
            error(f'No files specified for module {self.name}.')
            exit(1)

        # set library files dir
        self.librarydirs = f'-L{clone_libraries()}'
        # remove staging
        if path.exists(self.dir + '/stage'):
            rmtree(self.dir + '/stage')

        # define default values
        frameworksA = '-framework CoreFoundation -framework Foundation'
        librariesA = '-lsubstrate -lobjc' if self.type == 'tweak' else ''
        includesA = f'-I{clone_headers()}'
        archsA = ''
        sdkA = get_safe(module, 'sdk', '')

        # add module frameworks
        frameworks = get_safe(module, 'frameworks', [])
        if frameworks != []:
            for framework in frameworks:
                frameworksA += f' -framework {framework}'
        # set
        self.frameworks = frameworksA

        # add module libraries
        libraries = get_safe(module, 'libraries', [])
        if libraries != []:
            for library in libraries:
                librariesA += f' -l{library}'
        # set
        self.libraries = librariesA

        # add module include directories
        include = get_safe(module, 'include', [])
        if include != []:
            for include in include:
                includesA += f' -I{include}'
        # set
        self.include = includesA

        # add module architectures
        archs = get_safe(module, 'archs', ['arm64', 'arm64e'])
        if archs != []:
            for arch in archs:
                archsA += f' -arch {arch}'
        # set
        self.archs = archsA

        # attempt to manually find an sdk
        if sdkA == '':
            xcbuild = cmd_in_path('xcodebuild')
            if xcbuild is None:
                error(
                    'Xcode does not appear to be installed. Please specify an SDK manually.')
                exit(1)
            else:
                log_stdout('Finding an SDK...')
                sdkA = getoutput(
                    f'{xcbuild} -version -sdk iphoneos Path').split('\n')[-1]
                if sdkA == '':
                    error('Could not find an SDK. Please specify one manually.')
                    exit(1)
                remove_log_stdout('Finding an SDK...')
        else:
            # ensure sdk exists
            if not path.exists(sdkA):
                error(f'Specified SDK path "{sdkA}" does not exist.')
                exit(1)
        # set
        self.sdk = sdkA