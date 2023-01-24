# module imports
from os import makedirs
from pathlib import Path
from yaml import dump

# local imports
from ...common.logger import ask, error
from ...common.utils import resolve_path


class Module:
    def __init__(self):
        # dict to make YAML
        self.dict = {}
        
        # init control
        self.control = {}
        
        # ask for control values
        self.control['id'] = self.ask_for('id')
        self.control['name'] = self.ask_for('name', self.control['id'])
        self.control['version'] = self.ask_for('version', '1.0.0')
        self.control['maintainer'] = self.ask_for('maintainer')
        self.control['author'] = self.ask_for('author', self.control['maintainer'])
        self.control['depends'] = self.ask_for('dependencies', 'mobilesubstrate')
        self.control['architecture'] = self.ask_for('architecture', 'iphoneos-arm64')
        
        # add control to dict
        self.dict['control'] = self.control
        
    
    def write_to_file(self, path: Path = None) -> None:
        """Write the dict to a file.
        
        :param Path path: The path to write to.
        """
        path = resolve_path(f'{path}/LuzBuild')
        # make directory
        makedirs(path.parent, exist_ok=True)
        # dump yaml
        with open(path, 'w') as f:
            dump(self.dict, f)
    
    
    def ask_for(self, key: str, default: str = None) -> str:
        """Ask for a value.
        
        :param str key: The key to ask for.
        :param str default: The default value.
        :return: The value.
        """
        if default is not None:
            val = ask(f'What is this project\'s {key}? (enter for "{default}")')
            if val == '': return default
        else:
            val = ask(f'What is this project\'s {key}?')
            if val == '':
                error('You must enter a value.')
                exit(1)
        return val