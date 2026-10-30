# Copyright (c) 2026 Jaidan Arenas
# module imports
from inspect import stack
from pathlib import Path
from typing import Callable, Union

# local imports
from ...common.utils import resolve_path

# map of default values
default_values = {
    "tweak": {"frameworks": ["Foundation", "CoreFoundation"], "libraries": ["substrate", "root"]},
    "tool": {"frameworks": ["Foundation", "CoreFoundation"], "libraries": ["root"]},
    "preferences": {"frameworks": ["Foundation", "CoreFoundation", "UIKit", "Preferences"], "private_frameworks": ["Preferences"], "libraries": ["root"]},
    "library": {"frameworks": ["Foundation", "CoreFoundation"], "libraries": ["root"]},
    "framework": {"frameworks": ["Foundation", "CoreFoundation"], "libraries": ["root"]},
}


class Module:
    """Declare one binary, framework, tweak, or preference bundle.

    Paths in a ``Module`` declaration are resolved relative to the
    ``luzconf.py`` that constructed it, not to the shell's current directory.
    A module's type supplies sensible framework and library defaults; use an
    explicit empty ``libraries=[]`` only when intentionally opting out of
    Luz's default libraries (including Substrate for tweaks).

    ``type`` accepts ``"tweak"``, ``"tool"``, ``"preferences"``,
    ``"library"``, and ``"framework"``.  ``"prefs"`` and ``"lib"`` are
    retained as aliases for the corresponding long forms.
    """

    def __init__(
        self,
        files: Union[list, str],
        name: str,
        type: str = "tweak",
        install_name: str = "",
        install_dir: str = "",
        c_flags: list = None,
        swift_flags: list = None,
        linker_flags: list = None,
        optimization: int = 0,
        warnings: list = None,
        codesign_flags: list = None,
        filter: dict = None,
        public_headers: list = None,
        use_arc: bool = True,
        only_compile_changed: bool = True,
        bridging_headers: list = None,
        include_dirs: list = None,
        framework_dirs: list = None,
        library_dirs: list = None,
        frameworks: list = None,
        private_frameworks: list = None,
        libraries: list = None,
        before_stage: Callable = None,
        after_stage: Callable = None,
        resources_dir: Path = Path("./Resources"),
    ):
        """Create a module declaration for a ``Luz`` project.

        Args:
            files: One source path or a list of source paths.  Supported
                files may include C, Objective-C, Objective-C++, and Swift;
                relative paths are relative to this ``luzconf.py``.
            name: Logical module name.  It also determines default output,
                bundle, framework, and installation names.
            type: Module kind.  See the class documentation for values and
                aliases.  Defaults to ``"tweak"``.
            install_name: Filename installed in the package.  The default is
                ``<name>.dylib`` for tweaks/libraries and ``<name>`` for
                tools, frameworks, and preference bundles.
            install_dir: Absolute device-relative installation directory.
                Defaults depend on type: tools use ``/usr/local/bin``, tweaks
                use MobileSubstrate, libraries use ``/usr/lib``, frameworks
                use ``/Library/Frameworks``, and preferences use
                ``/Library/PreferenceBundles``.
            c_flags: Extra flags supplied while compiling C-family sources.
            swift_flags: Extra flags supplied while compiling Swift sources.
            linker_flags: Extra arguments passed to the linker driver.
            optimization: Optimization level passed as ``-O<level>``.
            warnings: Compiler warning flags.  Defaults to ``["-Wall"]``.
            codesign_flags: Flags given to ``ldid`` for device outputs;
                defaults to ``["-S"]``.
            filter: Tweak injection filter dictionary.  The default injects
                into ``com.apple.SpringBoard``; it is used only where a
                tweak filter plist is meaningful.
            public_headers: Headers exported by a library/framework package.
            use_arc: Add ``-fobjc-arc`` for Objective-C-family compilation.
            only_compile_changed: Reuse cached object files whose inputs and
                build settings have not changed.
            bridging_headers: Objective-C headers exposed to Swift sources.
            include_dirs: Extra header-search directories (``-I``).
            framework_dirs: Extra framework-search directories (``-F``).
            library_dirs: Extra library-search directories (``-L``).
            frameworks: Public frameworks to link.  Type defaults are added
                to this list.
            private_frameworks: Private frameworks to link.  Preference
                modules receive ``Preferences`` by default.
            libraries: Libraries without the ``lib`` prefix, for example
                ``["sqlite3"]``.  ``None`` uses type defaults; ``[]`` means
                no default libraries, useful for standalone tools.
            before_stage: Optional callable invoked before this module's
                files are copied into the package staging tree.
            after_stage: Optional callable invoked after staging, allowing a
                project to add generated package files.
            resources_dir: Resource directory copied for bundle-style module
                types.  Relative paths are relative to ``luzconf.py``.

        Raises:
            FileNotFoundError: If a source file or bridging header is absent.
            Exception: If ``files`` is empty or ``None``.
        """

        # assign variables
        self.type = type
        self.name = name
        self.files = files
        self.install_name = install_name
        self.install_dir = resolve_path(install_dir) if install_dir != "" else None
        self.c_flags = list(c_flags or [])
        self.swift_flags = list(swift_flags or [])
        self.linker_flags = list(linker_flags or [])
        self.optimization = optimization
        self.warnings = list(warnings or ["-Wall"])
        self.codesign_flags = list(codesign_flags or ["-S"])
        self.filter = dict(filter or {"bundles": ["com.apple.SpringBoard"]})
        self.public_headers = list(public_headers or [])
        self.use_arc = use_arc
        self.only_compile_changed = only_compile_changed
        self.bridging_headers = list(bridging_headers or [])
        self.include_dirs = list(include_dirs or [])
        self.framework_dirs = list(framework_dirs or [])
        self.library_dirs = list(library_dirs or [])
        self.frameworks = list(frameworks or [])
        self.private_frameworks = list(private_frameworks or [])
        # ``None`` selects Luz's compatibility defaults. An explicit empty
        # list is meaningful for modules that do not use a hooking runtime
        # (for example a constructor-only diagnostic tweak).
        self.libraries = None if libraries is None else list(libraries)
        self.before_stage = before_stage
        self.after_stage = after_stage

        # prefs -> preferences
        if self.type == "prefs":
            self.type = "preferences"

        # lib -> library
        if self.type == "lib":
            self.type = "library"

        # convert files to list
        if isinstance(self.files, str):
            self.files = [self.files]

        # check that files is not none
        if self.files is None:
            raise Exception("Files cannot be None")

        # check that files is not []
        if self.files == []:
            raise Exception("Files cannot be empty")

        # resolve files
        new_files = []

        # stack
        ins_stack = stack()[1]
        path = resolve_path(ins_stack.filename).absolute().parent
        for f in self.files:
            if not str(f).startswith("/"):
                f = f"{path}/{f}"
            new_files.append(f)

        # b_files
        b_files = [resolve_path(f) for f in new_files]
        self.files = []

        # see if files exist
        for f in b_files:
            # check if is list
            if isinstance(f, list):
                for ff in f:
                    if not ff.exists():
                        raise FileNotFoundError(f'File "{ff}" not found')
                    self.files.append(ff)
            else:
                if not f.exists():
                    raise FileNotFoundError(f'File "{f}" not found')
                self.files.append(f)

        # fix install name
        if self.install_name == "":
            if self.type == "tool" or self.type == "framework" or self.type == "preferences":
                self.install_name = self.name
            else:
                self.install_name = f"{self.name}.dylib"

        # install dir
        if self.install_dir is None:
            if self.type == "tool":
                self.install_dir = resolve_path("/usr/local/bin")
            elif self.type == "preferences":
                self.install_dir = resolve_path(f"/Library/PreferenceBundles/{self.name}.bundle")
            elif self.type == "tweak":
                self.install_dir = resolve_path(f"/Library/MobileSubstrate/DynamicLibraries")
            elif self.type == "library":
                self.install_dir = resolve_path(f"/usr/lib")
            elif self.type == "framework":
                self.install_dir = resolve_path(f"/Library/Frameworks/{self.name}.framework")

        # resolve bridging headers
        self.bridging_headers = [resolve_path(f if str(f).startswith("/") else path / f) for f in self.bridging_headers]

        # Public framework/library headers follow the same project-relative
        # path rules as sources. This is especially important for LuzGen
        # framework projects built with ``luz build --path <project>``.
        self.public_headers = [resolve_path(f if str(f).startswith("/") else path / f) for f in self.public_headers]

        # resources dir
        self.resources_dir = resolve_path(resources_dir if str(resources_dir).startswith("/") else path / resources_dir)

        # see if bridging headers exist
        for f in self.bridging_headers:
            if not f.exists():
                raise FileNotFoundError(f'Bridging header "{f}" not found')

        # resolve include dirs
        self.include_dirs = [str(resolve_path(f if str(f).startswith("/") else path / f).absolute()) for f in self.include_dirs]

        # resolve framework dirs
        self.framework_dirs = [str(resolve_path(f if str(f).startswith("/") else path / f).absolute()) for f in self.framework_dirs]

        # resolve library dirs
        self.library_dirs = [str(resolve_path(f if str(f).startswith("/") else path / f).absolute()) for f in self.library_dirs]

        # add default values
        if self.type in default_values:
            for key in default_values[self.type]:
                # An explicitly supplied library list opts out of the default
                # substrate runtime. Framework defaults remain additive.
                if key == "libraries" and self.libraries is not None:
                    continue
                if self.__dict__[key] is None:
                    self.__dict__[key] = []
                self.__dict__[key].extend(default_values[self.type][key])

    @property
    def abbreviated_name(self):
        """Return the stable three-character label used in Luz output."""
        if len(self.name) >= 3:
            return self.name[:3].upper()
        else:
            return (" " * (3 - len(self.name))) + self.name.upper()
