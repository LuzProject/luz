# local imports
from .components.framework import Framework
from .components.library import Library
from .components.prefs import Preferences
from .components.tool import Tool
from .components.tweak import Tweak


def assign(module, luz):
    # get type
    m_type = module.type

    # assign module
    if m_type == "tool":
        return Tool(module=module, luz=luz)
    elif m_type == "tweak":
        return Tweak(module=module, luz=luz)
    elif m_type == "preferences":
        return Preferences(module=module, luz=luz)
    elif m_type == "library":
        return Library(module=module, luz=luz)
    elif m_type == "framework":
        return Framework(module=module, luz=luz)
    else:
        raise Exception("Invalid module type.")
