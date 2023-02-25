# local imports
from ...common.utils import resolve_path


class Submodule:
    def __init__(self, path: str, inherit: bool = True):
        """Initialize submodule.

        :param str path: Path to submodule.
        :param bool inherit: Whether to inherit the hashlist from the parent.
        """
        # path
        self.path = resolve_path(path)
        self.name = self.path.name
