# local imports
from ..module import ModuleBuilder


class Library(ModuleBuilder):
    def __init__(self, **kwargs):
        """Build a tool module."""
        # kwargs parsing
        super().__init__(kwargs.get("module"), kwargs.get("luz"))
