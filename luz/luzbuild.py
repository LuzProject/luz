# module imports
from multiprocessing.pool import ThreadPool
from os import makedirs
from pyclang import CCompiler
from pydeb import Pack
from shutil import copytree
from subprocess import getoutput
from time import time
from yaml import safe_load

# local imports
from .logger import error, log, log_stdout, remove_log_stdout
from .modules.modules import assign_module
from .utils import cmd_in_path, exists, format_path, setup_luz_dir


class LuzBuild:
    def __init__(self, path_to_file: str = 'LuzBuild'):
        """Parse the luzbuild file.
        
        :param str path_to_file: The path to the luzbuild file.
        """
        
        # open and parse luzbuild file
        with open(path_to_file) as f:
            self.luzbuild = safe_load(f)
        
        # exit if failed
        if self.luzbuild is None or self.luzbuild == {}:
            error('Failed to parse LuzBuild file.')
            exit(1)
            
        # control
        self.control_raw = ''
        
        # prefix
        self.prefix = None
        
        # rootless
        self.rootless = True
        
        self.modules = {}
        
        # sdk
        self.sdk = ''

        for key in self.luzbuild:
            key = str(key).lower()
            value = self.luzbuild.get(key)
            
            # handle compiler metadata
            if key == 'meta':
                for k in value:
                    v = value.get(k)
                    k = str(k).lower()
                    if k == 'sdk':
                        self.sdk = v
                    elif k == 'rootless':
                        self.rootless = bool(v)
                    elif k == 'cc':
                        if self.prefix is not None:
                            prefix_path = cmd_in_path(self.prefix + '/' + v)
                            if not prefix_path:
                                error('Specified compiler is not in the prefix path.')
                                exit(1)
                            v = prefix_path
                        self.compiler = CCompiler().set_compiler(v)
                    elif k == 'archs':
                        self.archs = v
                    elif k == 'prefix':
                        if not exists(v):
                            error('Specified prefix path does not exist.')
                            exit(1)
                        self.prefix = format_path(v)
            
            # handle modules
            if key == 'modules':
                for m in value:
                    v = value.get(m)
                    v['archs'] = self.archs
                    v['prefix'] = self.prefix
                    self.modules[m] = assign_module(v, m, self.compiler, self)
            
            # control assignments
            if key == 'control':
                for c in value:
                    v = value.get(c)
                    c = str(c).lower()
                    # control assignments
                    if c in ['name', 'id', 'depends', 'architecture', 'version', 'maintainer', 'description', 'section', 'author', 'icon', 'priority', 'size', 'tags', 'replaces', 'provides', 'conflicts', 'installed-size', 'depiction', 'tag', 'package', 'sileodepiction']:
                        if type(v) is str:
                            # rootless architecture patch
                            if c == 'architecture' and self.rootless:
                                self.control_raw += 'Architecture: iphoneos-arm64\n'
                            # id patch
                            elif c == 'id':
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
        
        # ensure modules exist
        if self.modules == {}:
            error('No modules found in LuzBuild file.')
            exit(1)
        
        if self.compiler is None: self.compiler = CCompiler()
        
        # luzdir
        self.dir = setup_luz_dir()
        
    
    def get_sdk(self):
        """Get a default SDK using xcrun."""
        if self.sdk == '':
            xcrun = cmd_in_path('xcrun')
            if xcrun is None:
                error(
                    'Xcode does not appear to be installed. Please specify an SDK manually.')
                exit(1)
            else:
                log_stdout('Finding an SDK...')
                sdkA = getoutput(
                    f'{xcrun} --show-sdk-path --sdk iphoneos').split('\n')[-1]
                if sdkA == '' or not sdkA.startswith('/'):
                    error('Could not find an SDK. Please specify one manually.')
                    exit(1)
                remove_log_stdout('Finding an SDK...')
                self.sdk = sdkA
        return self.sdk
    
    
    def build(self):
        """Build the project."""
        start = time()
        with ThreadPool() as pool:
            for result in pool.map(lambda x: x.compile(rootless=self.rootless), self.modules.values()):
                if result is not None:
                    error(result)
                    exit(1)
        log_stdout('Packing up .deb file...')
        # make staging dirs
        if not exists(self.dir + '/stage/DEBIAN'):
            makedirs(self.dir + '/stage/DEBIAN')
        # write control
        with open(self.dir + '/stage/DEBIAN/control', 'w') as f:
            f.write(self.control_raw)
        self.__pack()
        remove_log_stdout('Packing up .deb file...')
        log(f'Done in {round(time() - start, 2)} seconds.')
          
  
    def __pack(self):
        """Pack up the .deb file."""
        # layout
        if exists('layout'):
            copytree('layout', self.dir + '/stage')
        # pack
        Pack(self.dir + '/stage')