# module imports
from os import getuid
from pwd import getpwuid
from pathlib import Path
from yaml import dump, safe_load

# local imports
from ...common.logger import ask, error
from ...common.tar import TAR
from ...common.utils import resolve_path


class Module:
    def __init__(self, module_type: str, src: str):
        # type
        self.type = module_type
        self.src = src

        # tar
        self.tar = TAR(algorithm='gzip')

        # templates_dir
        self.template_path = str(resolve_path(resolve_path(__file__).absolute()).parent.parent) + f'/templates/{self.type}/{self.src}.tar.gz'

        # dict to make YAML
        self.dict = {}

        # submodule
        self.submodule = False

        # check if luzbuild currently exists
        if resolve_path('LuzBuild').exists():
            val = ask(f'A LuzBuild was found in the current working directory. Would you like to add this module as a submodule? (y/n)')
            if val == '': val = 'n'
            if val.startswith('y'):
                self.submodule = True
        
        self.control = None
        
        if not self.submodule:
            # init control
            self.control = {}
            
            # ask for control values
            self.control['name'] = self.ask_for('name')
            self.control['id'] = self.ask_for('bundle ID', f'com.yourcompany.{self.control["name"]}')
            self.control['version'] = self.ask_for('version', '1.0.0')
            self.control['author'] = self.ask_for('author', getpwuid(getuid())[0], dsc='Who')
            self.control['maintainer'] = self.control['author']
            self.control['depends'] = self.ask_for('dependencies', 'mobilesubstrate', dsc1='are')
            self.control['architecture'] = self.ask_for('architecture', 'iphoneos-arm64')
            
            # add control to dict
            self.dict['control'] = self.control

    
    def write_to_file(self, path: Path = None) -> None:
        """Write the dict to a file.
        
        :param Path path: The path to write to.
        """
        if self.submodule:
            # add subproject
            luzbuild = None
            # read and add subproject
            with open('LuzBuild', 'r') as f:
                luzbuild = safe_load(f)
                if 'submodules' not in luzbuild.keys(): luzbuild['submodules'] = []
                luzbuild['submodules'].append(str(path))
            # dump yaml
            with open('LuzBuild', 'w') as f:
                dump(luzbuild, f)
        # resolve path
        path = resolve_path(f'{path}/LuzBuild')
        # extract archive to directory
        self.tar.decompress_archive(self.template_path, path.parent)
        # check for after_untar
        if hasattr(self, 'after_untar'): self.after_untar()
        # dump yaml
        with open(path, 'w') as f:
            dump(self.dict, f)
    
    
    def ask_for(self, key: str, default: str = None, dsc: str = 'What', dsc1: str = 'is') -> str:
        """Ask for a value.
        
        :param str key: The key to ask for.
        :param str default: The default value.
        :param str dsc: The descriptor of the question.
        :param str dsc1: The descriptor of the question.
        :return: The value.
        """
        if default is not None:
            val = ask(f'{dsc} {dsc1} this project\'s {key}? (enter for "{default}")')
            if val == '': return default
        else:
            val = ask(f'{dsc} {dsc1} this project\'s {key}?')
            if val == '':
                error('You must enter a value.')
                exit(1)
        return val