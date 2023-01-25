# local imports
from ...common.logger import error
from .tool import Tool
from .tweak import Tweak


def assign_module(type: str):
    """Assign the module to the correct class.

    :param str type: The type of module.
    """
    # args
    if type == 'tool':
        return Tool()
    elif type == 'tweak':
        return Tweak()
    else:
        error(f'Unknown module type: {type}')
        exit(1)
