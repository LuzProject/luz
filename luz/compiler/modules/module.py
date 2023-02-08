# local imports
from ..deps import clone_headers, clone_libraries
from ...common.logger import log, log_stdout, error, remove_log_stdout
from ...common.utils import get_from_cfg, get_from_default, resolve_path


def get_safe(module: dict, key: str, default: str = None) -> str:
    """Gets a key from a dict safely.
    
    :param dict module: The dict to get the key from.
    :param str key: The key to get.
    :param str default: The default value to return if the key is not found.
    :return: The value of the key.
    """
    return module.get(key) if module.get(key) is not None else default


class Module:
    def __init__(self, module: dict, key: str, luzbuild):
        """Module superclass.
        
        :param dict module: Module dictionary to build
        :param str key: Module key name
        :param LuzBuild luzbuild: Luzbuild class
        """
        # luzbuild
        self.luzbuild = luzbuild
        
        # dir
        self.dir = luzbuild.dir

        # stage dir
        self.stage_dir = resolve_path(f'{self.dir}/_')
        
        # type
        self.type = get_from_cfg(luzbuild, f'modules.{key}.type', 'modules.defaultType')

        # process
        self.filter = get_from_cfg(luzbuild, f'modules.{key}.filter', f'modules.types.{self.type}.filter')
        
        # install_dir
        self.install_dir = get_safe(module, 'installDir', None)

        # name
        self.name = key
        
        # frameworks
        self.frameworks = ''
        
        # private frameworks
        self.private_frameworks = ''
        
        # libraries
        self.libraries = ''
        
        # library files dir
        self.library_dirs = f'-L{clone_libraries(luzbuild)}'
        
        # include
        self.include = f'-I{clone_headers(luzbuild)}'
        
        # use arc
        self.arc = bool(get_from_cfg(luzbuild, f'modules.{key}.useArc', f'modules.types.{self.type}.useArc'))

        # only compile changes
        self.only_compile_changed = bool(get_from_cfg(luzbuild, f'modules.{key}.onlyCompileChanged', f'modules.types.{self.type}.onlyCompileChanged'))

        # ensure files are defined
        if module.get('files') is None or module.get('files') is [] or module.get('files') is '':
            error(f'No files specified for module "{self.name}".')
            exit(1)

        # define default values
        frameworksD = list(get_from_default(luzbuild, f'modules.types.{self.type}.frameworks'))
        private_frameworksD = list(get_from_default(luzbuild, f'modules.types.{self.type}.private_frameworks'))
        librariesD = list(get_from_default(luzbuild, f'modules.types.{self.type}.libraries'))

        # add module frameworks
        frameworks = get_safe(module, 'frameworks', [])
        # default frameworks first
        if frameworksD != []:
            for framework in frameworksD:
                self.frameworks += f' -framework {framework}'
        if frameworks != []:
            for framework in frameworks:
                self.frameworks += f' -framework {framework}'
        
        # add module private frameworks
        private_frameworks = get_safe(module, 'private_frameworks', [])
        # default frameworks first
        if private_frameworksD != []:
            for framework in private_frameworksD:
                self.private_frameworks += f' -framework {framework}'
        if private_frameworks != []:
            for framework in private_frameworks:
                self.private_frameworks += f' -framework {framework}'

        # add module libraries
        libraries = get_safe(module, 'libraries', [])
        # default frameworks first
        if librariesD != []:
            for library in librariesD:
                self.libraries += f' -l{library}'
        if libraries != []:
            for library in libraries:
                self.libraries += f' -l{library}'

        # add module include directories
        include = get_safe(module, 'include', [])
        if include != []:
            for include in include:
                self.include += f' -I{include}'

        # xcode sdks dont include private frameworks
        if self.private_frameworks != '' and self.sdk.startswith('/Applications'):
            error(f'No SDK specified. Xcode will be used, and private frameworks will not be found.')
            exit(1)
            
    def log(self, msg): log(msg, self.luzbuild.lock)
    def error(self, msg): error(msg, self.luzbuild.lock)
    def log_stdout(self, msg): log_stdout(msg, self.luzbuild.lock)
    def remove_log_stdout(self, msg): remove_log_stdout(msg, self.luzbuild.lock)