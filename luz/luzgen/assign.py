# Copyright (c) 2026 Jaidan Arenas
# local imports
from ..common.logger import error
from .components.framework import Framework
from .components.library import Library
from .components.prefs import Preferences
from .components.tool import Tool
from .components.tweak import Tweak


def assign_module(type: str):
    """Assign the module to the correct class.

    :param str type: The type of module.
    """
    # args
    if type == "tool":
        return Tool()
    elif type == "tweak":
        return Tweak()
    elif type == "prefs":
        return Preferences()
    elif type == "preferences":
        return Preferences()
    elif type in ("library", "lib"):
        return Library()
    elif type in ("framework", "fw"):
        return Framework()
    else:
        error(f"Unknown module type: {type}")
        exit(1)
