# module imports
from pyclang import CCompiler

# local imports
from ..logger import error
from .tool import Tool
from .tweak import Tweak


def assign_module(module: dict, key: str, compiler: CCompiler, luzbuild):
    """Assign the module to the correct class.

    :param dict module: The module dict.
    :param str key: The key of the module.
    :param CCompiler compiler: The compiler object.
    :return: The module object.
    """
    if module.get('type') == 'tool':
        return Tool(module=module, key=key, compiler=compiler, luzbuild=luzbuild)
    elif module.get('type') == 'tweak':
        return Tweak(module=module, key=key, compiler=compiler, luzbuild=luzbuild)
    else:
        error(f'Unknown module type: {module.get("type")}')
        exit(1)