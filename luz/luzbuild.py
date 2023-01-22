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
from .logger import error, log, log_stdout, remove_log_stdout
from .modules.modules import assign_module
from .utils import cmd_in_path, setup_luz_dir


class LuzBuild:
    def __init__(self, path: str = 'LuzBuild'):
        """Parse the luzbuild file.
        
        :param str path: The path to the luzbuild file.
        """
        
        # open and parse luzbuild file
        with open(path) as f:
            self.luzbuild = safe_load(f)
        
        # exit if failed
        if self.luzbuild is None or self.luzbuild == {}:
            error('Failed to parse LuzBuild file.')
            exit(1)
            
        # control
        self.control_raw = ''
        
        # rootless
        self.rootless = True
        
        self.modules = {}
        
        # sdk
        self.sdk = ''
        
        if self.luzbuild.get('CC') is not None:
            self.compiler = CCompiler().set_compiler(self.luzbuild.get('CC'))
        else:
            self.compiler = CCompiler

        for key in self.luzbuild:
            value = self.luzbuild.get(key)
            # rootless
            if key == 'rootless':
                self.rootless = bool(value)
            # control assignments
            if key in ['name', 'id', 'depends', 'architecture', 'version', 'maintainer', 'description', 'section', 'author', 'homepage', 'icon', 'priority', 'size', 'tags', 'replaces', 'provides', 'conflicts', 'installed-size', 'depiction']:
                if type(value) is str:
                    if key == 'architecture' and self.rootless:
                        self.control_raw += 'Architecture: iphoneos-arm64\n'
                    elif key == 'id':
                        self.control_raw += f'Package: {value}\n'
                    else:
                        self.control_raw += f'{key.capitalize()}: {value}\n'
            # add modules
            if type(value) is dict:
                self.modules[key] = assign_module(value, key, self.compiler, self)
        
        # ensure modules exist
        if self.modules == {}:
            error('No modules found in LuzBuild file.')
            exit(1)
        
        # luzdir
        self.dir = setup_luz_dir()
        
    
    def get_sdk(self):
        """Get a default SDK using xcrun."""
        print('here (sdk)')
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
                if sdkA == '':
                    error('Could not find an SDK. Please specify one manually.')
                    exit(1)
                remove_log_stdout('Finding an SDK...')
                self.sdk = sdkA
        return self.sdk
    
    
    def build(self):
        """Build the project."""
        print('here (build)')
        start = time()
        with ThreadPool() as pool:
            for result in pool.map(lambda x: x.compile(rootless=self.rootless), self.modules.values()):
                if result is not None:
                    error(result)
                    exit(1)
        log_stdout('Packing up .deb file...')
        # make staging dirs
        if not path.exists(self.dir + '/stage/DEBIAN'):
            makedirs(self.dir + '/stage/DEBIAN')
        # write control
        with open(self.dir + '/stage/DEBIAN/control', 'w') as f:
            f.write(self.control_raw)
        self.__pack()
        remove_log_stdout('Packing up .deb file...')
        log(f'Done in {round(time() - start, 2)} seconds.')
          
  
    def __pack(self):
        """Pack up the .deb file."""
        print('here (pack)')
        # layout
        if path.exists('layout'):
            copytree('layout', self.dir + '/stage')
        # pack
        Pack(self.dir + '/stage')