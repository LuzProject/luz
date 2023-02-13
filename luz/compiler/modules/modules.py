# local imports
from ...common.logger import error
from .tool import Tool
from .tweak import Tweak
from .prefs import Preferences


def assign_module(module: dict, key: str, luzbuild):
    """Assign the module to the correct class.

    :param dict module: The module dict.
    :param str key: The key of the module.
    :param LuzBuild luzbuild: The LuzBuild class.
    :return: The module object.
    """
    # args
    args = {'module': module, 'key': key, 'luzbuild': luzbuild}
    if module.get('type') == 'tool':
        return Tool(**args)
    elif module.get('type') == 'tweak':
        return Tweak(**args)
    elif module.get('type') == 'preferences':
        return Preferences(**args)
    else:
        error(f'Unknown module type: {module.get("type")}')
        exit(1)