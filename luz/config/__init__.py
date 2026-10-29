"""Public declarations available to every ``luzconf.py``.

Import from this module instead of internal implementation paths::

    from luz.config import Control, Luz, Meta, Module, Script, Submodule

``Meta`` configures a destination/toolchain, ``Control`` configures Debian
metadata, and ``Module`` declares source outputs.  ``Script`` adds Debian
maintainer hooks and ``Submodule`` includes a child project.  ``Luz`` ties
those declarations together and exposes build, clean, and install actions.
"""

# import all the components
from .components.control import Control
from .components.meta import Meta
from .components.module import Module
from .components.script import Script
from .components.submodule import Submodule

# luz
from .luz import Luz

__all__ = ("Control", "Luz", "Meta", "Module", "Script", "Submodule")
