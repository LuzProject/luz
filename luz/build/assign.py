# local imports
from .components.tool import Tool
from .components.tweak import Tweak
from .components.prefs import Preferences


def assign(module, luz):
    # get type
    m_type = module.type

    # assign module
    if m_type == "tool":
        return Tool(module=module, luz=luz)
    elif m_type == "tweak":
        return Tweak(module=module, luz=luz)
    elif m_type == "preferences" or m_type == "prefs":
        return Preferences(module=module, luz=luz)
    else:
        raise Exception("Invalid module type.")
