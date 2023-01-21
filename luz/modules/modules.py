# module imports
from pyclang import CCompiler

# local imports
from ..logger import error
from .tool import Tool
from .tweak import Tweak


def assign_module(module: dict, key: str, compiler: CCompiler, control: str):
    """Assign the module to the correct class.

    :param dict module: The module dict.
    :param str key: The key of the module.
    :param CCompiler compiler: The compiler object.
    :param str control: The control string.
    :return: The module object.
    """
    if module.get('type') == 'tool':
        return Tool(module, key, compiler, control)
    elif module.get('type') == 'tweak':
        return Tweak(module, key, compiler, control)
    else:
        error(f'Unknown module type: {module.get("type")}')
        exit(1)