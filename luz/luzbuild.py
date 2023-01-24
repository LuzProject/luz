# module imports
from multiprocessing.pool import ThreadPool
from os import makedirs, path
from pyclang import CCompiler
from pydeb import Pack
from shutil import copytree
from subprocess import getoutput
from time import time
from yaml import safe_load

# local imports
from .logger import error, log, log_stdout, remove_log_stdout, warn
from .modules.modules import assign_module
from .utils import cmd_in_path, exists, get_from_cfg, get_luz_storage, setup_luz_dir


class LuzBuild:
    def __init__(self, path_to_file: str = 'LuzBuild'):
        """Parse the luzbuild file.
        
        :param str path_to_file: The path to the luzbuild file.
        """
        # module path
        module_path = path.dirname(path.realpath(__file__))
        # read default config values
        with open(module_path + '/config/defaults.yaml') as f:
            self.defaults = safe_load(f)
        
        # open and parse luzbuild file
        with open(path_to_file) as f:
            self.luzbuild = safe_load(f)
        
        # exit if failed
        if self.luzbuild is None or self.luzbuild == {}:
            error('Failed to parse LuzBuild file.')
            exit(1)
            
        # control
        self.control_raw = ''
        
        # sdk
        self.sdk = get_from_cfg(self, 'meta.sdk')
        
        # prefix
        self.prefix = get_from_cfg(self, 'meta.prefix')
        
        # cc
        self.cc = get_from_cfg(self, 'meta.cc')
        
        # rootless
        self.rootless = get_from_cfg(self, 'meta.rootless')
        
        # optimization
        self.optimization = get_from_cfg(self, 'meta.optimization')
        
        # warnings
        self.warnings = get_from_cfg(self, 'meta.warnings')
        
        # entitlement flag
        self.entflag = get_from_cfg(self, 'meta.entflag')
        
        # entitlement file
        self.entfile = get_from_cfg(self, 'meta.entfile')
                
        # compression
        self.compression = get_from_cfg(self, 'meta.compression')
        
        # archs
        self.archs = ''
        archs = get_from_cfg(self, 'meta.archs')
        
        for arch in archs:
            self.archs += f' -arch {arch}'
            
        # platform
        self.platform = get_from_cfg(self, 'meta.platform')
        
        # min version
        self.minVers = get_from_cfg(self, 'meta.minVers')
            
        # storage dir
        self.storage = get_luz_storage()
        
        # ensure prefix exists
        if self.prefix is not '' and not exists(self.prefix):
            error('Specified prefix does not exist.')
            exit(1)
        
        # format cc with prefix
        if self.prefix is not '' and not self.cc.startswith('/'):
            prefix_path = cmd_in_path(self.prefix + '/' + self.cc)
            if not prefix_path:
                error(
                    f'Compiler "{self.cc}" not in prefix path.')
                exit(1)
            self.cc = prefix_path
            
        # attempt to manually find an sdk
        if self.sdk == '':
            self.sdk = self.__get_sdk()
        else:
            # ensure sdk exists
            if not exists(self.sdk):
                error(f'Specified SDK path "{self.sdk}" does not exist.')
                exit(1)
        
        # modules
        self.modules = {}

        # parse luzbuild file
        with ThreadPool() as pool:
            for result in pool.map(lambda x: self.__handle_key(x), self.luzbuild):
                pass
        
        # ensure modules exist
        if self.modules == {}:
            error('No modules found in LuzBuild file.')
            exit(1)
        
        
    def __handle_key(self, key):
        """Handle a key in the LuzBuild file.
        
        :param str key: The key to handle.
        """
        key = str(key).lower()
        value = self.luzbuild.get(key)

        # handle modules
        if key == 'modules':
            # dir
            self.dir = setup_luz_dir()
            # set compiler
            self.compiler = CCompiler().set_compiler(self.cc)
            for m in value:
                v = value.get(m)
                self.modules[m] = assign_module(v, m, self)

        # control assignments
        if key == 'control':
            for c in value:
                v = value.get(c)
                c = str(c).lower()
                # control assignments
                if c in ['name', 'id', 'depends', 'architecture', 'version', 'maintainer', 'description', 'section', 'author', 'icon', 'priority', 'size', 'tags', 'replaces', 'provides', 'conflicts', 'installed-size', 'depiction', 'tag', 'package', 'sileodepiction']:
                    if type(v) is str:
                        # id patch
                        if c == 'id':
                            self.control_raw += f'Package: {v}\n'
                        # sileodepiction patch
                        elif c == 'sileodepiction':
                            self.control_raw += f'SileoDepiction: {v}\n'
                        # installed-size patch
                        elif c == 'installed-size':
                            self.control_raw += f'Installed-Size: {v}\n'
                        # other values
                        else:
                            self.control_raw += f'{c.capitalize()}: {v}\n'

    
    def __get_sdk(self):
        """Get an SDK from Xcode using xcrun."""
        xcrun = cmd_in_path('xcrun')
        if xcrun is None:
            error(
                'Xcode does not appear to be installed. Please specify an SDK manually.')
            exit(1)
        else:
            warn('Looking for default SDK. This will add time to the build process.')
            log_stdout('Finding an SDK...')
            sdkA = getoutput(
                f'{xcrun} --show-sdk-path --sdk iphoneos').split('\n')[-1]
            if sdkA == '' or not sdkA.startswith('/'):
                error('Could not find an SDK. Please specify one manually.')
                exit(1)
            remove_log_stdout('Finding an SDK...')
            self.sdk = sdkA
        return self.sdk
    
    
    def __pack(self):
        """Pack up the .deb file."""
        # layout
        if exists('layout'):
            copytree('layout', self.dir + '/stage', dirs_exist_ok=True)
        # pack
        Pack(self.dir + '/stage', algorithm=self.compression)
    
    
    def build(self):
        """Build the project."""
        start = time()
        with ThreadPool() as pool:
            for result in pool.map(lambda x: x.compile(), self.modules.values()):
                if result is not None:
                    error(result)
                    exit(1)
        # make staging dirs
        if not exists(self.dir + '/stage/DEBIAN'):
            makedirs(self.dir + '/stage/DEBIAN')
        # write control
        with open(self.dir + '/stage/DEBIAN/control', 'w') as f:
            f.write(self.control_raw)
        self.__pack()
        remove_log_stdout('Packing up .deb file...')
        log(f'Done in {round(time() - start, 2)} seconds.')