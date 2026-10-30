# Copyright (c) 2026 Jaidan Arenas
"""Interactive generator for framework projects."""

from .library import Library


class Framework(Library):
    """Generate a starter framework with resources and an Objective-C header."""

    def __init__(self):
        super().__init__(module_type="framework")
