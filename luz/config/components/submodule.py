# Copyright (c) 2026 Jaidan Arenas
# local imports
from ...common.utils import resolve_path


class Submodule:
    """Include another Luz project as part of this project build.

    Submodules are useful for a shared library or companion package that
    should build before the parent package.  The parent records the resolved
    configuration path and a stable name; build orchestration decides whether
    its cached hashes can be inherited.
    """

    def __init__(self, path: str, inherit: bool = True):
        """Create a subproject declaration.

        Args:
            path: Path to the child project's configuration file or project
                directory, resolved to an absolute path.
            inherit: Reuse the parent's build hash list when possible.  Leave
                enabled for ordinary dependent projects; disable it when the
                child must always evaluate its own source-state cache.
        """
        # path
        self.path = resolve_path(path)
        self.name = self.path.name
        self.inherit = inherit
