# module imports
from os import makedirs, getuid
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
        self.template_path = str(resolve_path(resolve_path(__file__).absolute()).parent.parent) + f'/templates/{self.type}s/{self.src}.tar.gz'

        # dict to make YAML
        self.dict = {}
        
        # init control
        self.control = {}
        
        # ask for control values
        self.control['id'] = self.ask_for('id')
        self.control['name'] = self.ask_for('name', self.control['id'])
        self.control['version'] = self.ask_for('version', '1.0.0')
        self.control['maintainer'] = self.ask_for('maintainer', getpwuid(getuid())[0], dsc='Who')
        self.control['author'] = self.ask_for('author', self.control['maintainer'], dsc='Who')
        self.control['depends'] = self.ask_for('dependencies', 'mobilesubstrate', dsc1='are')
        self.control['architecture'] = self.ask_for('architecture', 'iphoneos-arm64')
        
        # add control to dict
        self.dict['control'] = self.control
        
    
    def write_to_file(self, path: Path = None) -> None:
        """Write the dict to a file.
        
        :param Path path: The path to write to.
        """
        # check if luzbuild currently exists
        if resolve_path('LuzBuild').exists():
            val = ask(f'A LuzBuild was found in the current working directory. Would you like to add this module as a submodule? (y/n)')
            if val.startswith('y'):
                # add subproject
                luzbuild = None
                # read and add subproject
                with open('LuzBuild', 'r') as f:
                    luzbuild = safe_load(f)
                    if luzbuild['submodules'] is None: luzbuild['submodules'] = []
                    luzbuild['submodules'].append(str(path))
                # dump yaml
                with open('LuzBuild', 'w') as f:
                    dump(luzbuild, f)
        # resolve path
        path = resolve_path(f'{path}/LuzBuild')
        # extract archive to directory
        self.tar.decompress_archive(self.template_path, path.parent)
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