# Copyright (c) 2026 Jaidan Arenas
# module imports
from inspect import stack

# local imports
from ...common.utils import resolve_path


class Script:
    """Add one executable Debian maintainer-script lifecycle hook.

    A script can be loaded from a project-relative file or supplied inline.
    Luz writes it to ``DEBIAN/<script_type>`` and marks it executable while
    packaging.  Only Debian's four binary-package hooks are supported; this
    avoids silently shipping files that ``dpkg`` will never invoke.
    """

    def __init__(self, script_type: str, path: str = None, content: str = None):
        """Create a maintainer script declaration.

        Args:
            script_type: Lifecycle hook: ``"preinst"`` before unpacking,
                ``"postinst"`` after configuration, ``"prerm"`` before
                removal, or ``"postrm"`` after removal.
            path: Existing script file.  A relative path is resolved against
                the ``luzconf.py`` that creates this object.
            content: Inline script text, including an optional shebang.
                Exactly one of ``path`` or ``content`` should normally be
                supplied; a path wins when both are present.

        Raises:
            ValueError: If ``script_type`` is not a Debian maintainer hook.
            FileNotFoundError: If ``path`` does not exist.
            Exception: If neither a path nor inline content is supplied.
        """

        # Debian recognizes only these maintainer-script lifecycle hooks.
        # Validate at configuration time instead of silently placing a file
        # dpkg will never execute into DEBIAN/.
        valid_types = {"preinst", "postinst", "prerm", "postrm"}
        if script_type not in valid_types:
            raise ValueError(f"Unsupported maintainer script type '{script_type}'.")
        self.type = script_type

        # stack
        ins_stack = stack()[1]
        cwd = resolve_path(ins_stack.filename).parent

        # path
        if path is not None:
            if not path.startswith("/"):
                path = f"{cwd}/{path}"
            self.path = resolve_path(path)
            if not self.path.exists():
                raise FileNotFoundError(f"Script path {self.path} does not exist.")
            else:
                self.content = self.path.read_text()
        elif content is not None:
            self.content = content
        else:
            raise Exception(f"Either path or content must be set for script of type {script_type}.")
