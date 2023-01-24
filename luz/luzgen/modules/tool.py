# local imports
from ...common.logger import ask, error
from ...common.utils import resolve_path
from .module import Module


class Tool(Module):
    def __init__(self):
        # init super class
        super().__init__()
        # type
        self.type = 'tool'
        # get keys
        self.name = self.__ask_for('name')
        # add values to dict
        self.dict.update({'modules': {self.name: {'files': []}}})
        # folder
        folder = resolve_path(self.__ask_for('folder for project', self.control['name']))
        # write to yaml
        self.write_to_file(folder)
        
    
    def __ask_for(self, key: str, default: str = None) -> str:
        """Ask for a value.
        
        :param str key: The key to ask for.
        :param str default: The default value.
        :return: The value.
        """
        if default is not None:
            val = ask(f'What is this {self.type}\'s {key}? (enter for "{default}")')
            if val == '': return default
        else:
            val = ask(f'What is this {self.type}\'s {key}?')
            if val == '':
                error('You must enter a value.')
                exit(1)
        return val