# local imports
from ..common.utils import resolve_path

# import components
from .components.meta import Meta

class Luz():
    def __init__(self, file_path: str = 'luz-b.py'):
        """Initialize Luz
        
        :param str file_path: Path to luz.py
        """
        # ensure that the file exists
        if not resolve_path(file_path).exists():
            raise FileNotFoundError(f'File {file_path} not found')

        # split file
        file_path = file_path.split('.py')[0]
        
        # import file
        self.__luz_raw = __import__(file_path)

        # meta
        self.meta = getattr(self.__luz_raw, 'meta', Meta())

        # control
        self.control = getattr(self.__luz_raw, 'control', None)

        # modules
        self.modules = getattr(self.__luz_raw, 'modules', [])

        # submodules
        self.submodules = getattr(self.__luz_raw, 'submodules', [])