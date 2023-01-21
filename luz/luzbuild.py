# module imports
from multiprocessing.pool import ThreadPool
from pyclang import CCompiler
from pydeb import Pack
from time import time
from yaml import safe_load

# local imports
from .logger import error, log, log_stdout, remove_log_stdout
from .modules.modules import assign_module
from .utils import setup_luz_dir

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
                self.modules[key] = assign_module(value, key, self.compiler, self.control_raw)
        
        # ensure modules exist
        if self.modules == {}:
            error('No modules found in LuzBuild file.')
            exit(1)
        
    
    def build(self):
        """Build the project."""
        start = time()
        with ThreadPool() as pool:
            for result in pool.map(lambda x: x.compile(rootless=self.rootless), self.modules.values()):
                if result is not None:
                    error(result)
                    exit(1)
        log_stdout('Packing up .deb file...')
        self.__pack()
        remove_log_stdout('Packing up .deb file...')
        log(f'Done in {round(time() - start, 2)} seconds.')
          
  
    def __pack(self):
        """Pack up the .deb file."""
        # dir
        dir = setup_luz_dir()
        # pack
        Pack(dir + '/stage')