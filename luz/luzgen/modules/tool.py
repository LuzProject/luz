# local imports
from ...common.logger import ask, error
from ...common.utils import resolve_path
from .module import Module


class Tool(Module):
    def __init__(self):
        # type
        self.type = 'tool'
        # valid source types
        self.VALID = ['objc', 'c', 'asm', 'objcpp', 'swift']
        # srctype
        self.srctype = self.__ask_for('source type', 'objc').lower()
        if self.srctype not in self.VALID:
            error(f'Invalid source type: {self.srctype}. Valid types: {", ".join(self.VALID)}')
            exit(1)

        # init super class
        super().__init__(self.type, self.srctype)

        # calculate ending
        if self.srctype == 'objc': self.ending = '.m'
        elif self.srctype == 'c': self.ending = '.c'
        elif self.srctype == 'asm': self.ending = '.s'
        elif self.srctype == 'objcpp': self.ending = '.mm'
        elif self.srctype == 'swift': self.ending = '.swift'

        # get keys
        self.name = self.__ask_for('name')
        # add values to dict
        self.dict.update({'modules': {self.name: {'files': []}}})
        # folder
        folder = resolve_path(self.__ask_for('folder for project', self.control['name']))
        # write to yaml
        self.write_to_file(folder)
        
    
    def __ask_for(self, key: str, default: str = None, dsc: str = 'What', dsc1: str = 'is') -> str:
        """Ask for a value.
        
        :param str key: The key to ask for.
        :param str default: The default value.
        :param str dsc: The descriptor of the question.
        :param str dsc1: The descriptor of the question.
        :return: The value.
        """
        if default is not None:
            val = ask(f'{dsc} {dsc1} this {self.type}\'s {key}? (enter for "{default}")')
            if val == '': return default
        else:
            val = ask(f'{dsc} {dsc1} this {self.type}\'s {key}?')
            if val == '':
                error('You must enter a value.')
                exit(1)
        return val