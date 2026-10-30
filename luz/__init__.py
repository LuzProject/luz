# Copyright (c) 2026 Jaidan Arenas
"""Luz's concise public API for use in a project ``luzconf.py``.

Typical configurations import the declarations directly from :mod:`luz`::

    from luz import Control, Luz, Meta, Module

Each declaration has detailed parameter documentation for editor hover help.
For the full configuration namespace, :mod:`luz.config` exports the same
objects plus :class:`Script` and :class:`Submodule`.
"""

from .config import Control, Luz, Meta, Module, Script, Submodule

__all__ = ("Control", "Luz", "Meta", "Module", "Script", "Submodule")
