# module imports
from multiprocessing.pool import ThreadPool
from os import makedirs
from pathlib import Path
from pyclang import CCompiler
from pydeb import Pack
from shutil import copytree, rmtree
from subprocess import getoutput
from time import time
from yaml import safe_load

# local imports
from ..common.logger import error, log, log_stdout, remove_log_stdout, warn
from .modules.modules import assign_module
from ..common.utils import cmd_in_path, get_from_cfg, get_from_luzbuild, get_luz_storage, resolve_path, setup_luz_dir


class LuzBuild:
    def __init__(self, clean: bool = False, path_to_file: str = 'LuzBuild'):
        """Parse the luzbuild file.
        
        :param str path_to_file: The path to the luzbuild file.
        """
        # module path
        module_path = resolve_path(resolve_path(__file__).absolute()).parent
        # read default config values
        with open(f'{module_path}/config/defaults.yaml') as f: self.defaults = safe_load(f)
        
        # open and parse luzbuild file
        with open(path_to_file) as f: self.luzbuild = safe_load(f)
        
        # exit if failed
        if self.luzbuild is None or self.luzbuild == {}:
            error('Failed to parse LuzBuild file.')
            exit(1)
        
        # clean
        if clean:
            rmtree('.luz', ignore_errors=True)
            
        # control
        self.control_raw = ''
        
        # sdk
        self.sdk = get_from_cfg(self, 'meta.sdk')
        
        # prefix
        self.prefix = get_from_cfg(self, 'meta.prefix')
        
        # cc
        self.cc = get_from_cfg(self, 'meta.cc')
        
        # swiftc
        self.swift = get_from_cfg(self, 'meta.swiftc')
        
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
        
        for arch in archs: self.archs += f' -arch {arch}'
            
        # platform
        self.platform = get_from_cfg(self, 'meta.platform')
        
        # min version
        self.min_vers = get_from_cfg(self, 'meta.minVers')
            
        # storage dir
        self.storage = get_luz_storage()
        
        # ensure prefix exists
        if self.prefix is not '':
            self.prefix = resolve_path(self.prefix)
            if not self.prefix.exists():
                error('Specified prefix does not exist.')
                exit(1)
        
        # format cc with prefix
        if self.prefix is not '' and not resolve_path(self.cc).is_relative_to('/'):
            prefix_path = cmd_in_path(f'{self.prefix}/{self.cc}')
            if not prefix_path:
                error(
                    f'C compiler "{self.cc}" not in prefix path.')
                exit(1)
            self.cc = prefix_path
        
        # format swift with prefix
        if self.prefix is not '' and not resolve_path(self.swift).is_relative_to('/'):
            prefix_path = cmd_in_path(f'{self.prefix}/{self.swift}')
            if not prefix_path:
                error(
                    f'Swift compiler "{self.swift}" not in prefix path.')
                exit(1)
            self.swift = prefix_path
            
        # attempt to manually find an sdk
        if self.sdk == '': self.sdk = self.__get_sdk()
        else:
            # ensure sdk exists
            self.sdk = resolve_path(self.sdk)
            if not self.sdk.exists():
                error(f'Specified SDK path "{self.sdk}" does not exist.')
                exit(1)
        
        # modules
        self.modules = get_from_luzbuild(self, 'modules')
        
        # parse modules
        if self.modules is not None:
            # dir
            self.dir = setup_luz_dir()
            # set compiler
            self.compiler = CCompiler().set_compiler(self.cc)
            for m in self.modules:
                v = self.modules.get(m)
                if type(self.swift) is not Path:
                    for f in v.get('files'):
                        if '.swift' in f:
                            self.swift = cmd_in_path(self.swift)
                            if self.swift is None:
                                error('Swift compiler not found.')
                                exit(1)
                            break
                self.modules[m] = assign_module(v, m, self)
        elif self.modules is None or self.modules == {}:
            error('No modules found in LuzBuild file.')
            exit(1)

        # parse luzbuild file
        with ThreadPool() as pool:
            for result in pool.map(lambda x: self.__handle_key(x), self.luzbuild):
                pass
        
        
    def __handle_key(self, key):
        """Handle a key in the LuzBuild file.
        
        :param str key: The key to handle.
        """
        key = str(key).lower()
        value = self.luzbuild.get(key)

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
                f'{xcrun} --show-sdk-path --sdk {self.platform}').split('\n')[-1]
            if sdkA == '' or not sdkA.startswith('/'):
                error('Could not find an SDK. Please specify one manually.')
                exit(1)
            remove_log_stdout('Finding an SDK...')
            self.sdk = sdkA
        return resolve_path(self.sdk)
    
    
    def __pack(self):
        """Pack up the .deb file."""
        # layout
        layout_path = resolve_path('layout')
        if layout_path.exists(): copytree(layout_path, f'{self.dir}/stage', dirs_exist_ok=True)
        # pack
        Pack(f'{self.dir}/stage', algorithm=self.compression)
    
    
    def build(self):
        """Build the project."""
        log(f'Compiling for target "{self.platform}:{self.min_vers}"...')
        start = time()
        with ThreadPool() as pool:
            for result in pool.map(lambda x: x.compile(), self.modules.values()):
                if result is not None:
                    error(result)
                    exit(1)
        # make staging dirs
        if not resolve_path(f'{self.dir}/stage/DEBIAN').exists():
            makedirs(f'{self.dir}/stage/DEBIAN')
        # write control
        with open(f'{self.dir}/stage/DEBIAN/control', 'w') as f:
            f.write(self.control_raw)
        self.__pack()
        remove_log_stdout('Packing up .deb file...')
        log(f'Done in {round(time() - start, 2)} seconds.')