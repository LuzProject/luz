# module imports
from inspect import stack
from pathlib import Path
from typing import Callable, Union

# local imports
from ...common.utils import resolve_path

# map of default values
default_values = {
    "tweak": {"frameworks": ["Foundation", "CoreFoundation"], "libraries": ["substrate", "System"]},
    "tool": {"frameworks": ["Foundation", "CoreFoundation"], "libraries": ["System"]},
    "preferences": {"frameworks": ["Foundation", "CoreFoundation"], "private_frameworks": ["preferences"], "libraries": ["System"]},
    "library": {"frameworks": ["Foundation", "CoreFoundation"], "libraries": ["System"]},
    "framework": {"frameworks": ["Foundation", "CoreFoundation"], "libraries": ["System"]},
}


class Module:
    def __init__(
        self,
        files: Union[list, str],
        name: str,
        type: str = "tweak",
        install_name: str = "",
        install_dir: str = "",
        c_flags: list = [],
        swift_flags: list = [],
        linker_flags: list = [],
        optimization: int = 0,
        warnings: list = ["-Wall"],
        codesign_flags: list = ["-S"],
        filter: dict = {"bundles": ["com.apple.SpringBoard"]},
        public_headers: list = [],
        use_arc: bool = True,
        only_compile_changed: bool = True,
        bridging_headers: list = [],
        include_dirs: list = [],
        framework_dirs: list = [],
        library_dirs: list = [],
        frameworks: list = [],
        private_frameworks: list = [],
        libraries: list = [],
        before_stage: Callable = None,
        after_stage: Callable = None,
        resources_dir: Path = Path("./Resources"),
    ):
        """Initialize Module

        Args:
            files (Union[list, str]): Files to compile
            name (str): Name of module
            type (str, optional): Type of module (default: tweak)
            install_name (str, optional): Name to install the module as (defaults to the module name)
            install_dir (str, optional): Directory to install the module to
            c_flags (list, optional): C flags
            swift_flags (list, optional): Swift flags
            linker_flags (list, optional): Linker flags
            optimization (int, optional): Optimization level (default: 0)
            warnings (list, optional): Warnings (default: -Wall)
            codesign_flags (list, optional): Entitlements flag (default: -S)
            filter (dict, optional): Filter
            use_arc (bool, optional): Use ARC (default: True)
            only_compile_changed (bool, optional): Only compile changed files (default: True)
            bridging_headers (list, optional): Bridging headers
            include_dirs (list, optional): Include directories
            framework_dirs (list, optional): Framework directories
            library_dirs (list, optional): Library directories
            frameworks (list, optional): Frameworks to link
            private_frameworks (list, optional): Private frameworks to link
            libraries (list, optional): Libraries to link
        """

        # assign variables
        self.type = type
        self.name = name
        self.files = files
        self.install_name = install_name
        self.install_dir = resolve_path(install_dir) if install_dir != "" else None
        self.c_flags = c_flags
        self.swift_flags = swift_flags
        self.linker_flags = linker_flags
        self.optimization = optimization
        self.warnings = warnings
        self.codesign_flags = codesign_flags
        self.filter = filter
        self.public_headers = public_headers
        self.use_arc = use_arc
        self.only_compile_changed = only_compile_changed
        self.bridging_headers = bridging_headers
        self.include_dirs = include_dirs
        self.framework_dirs = framework_dirs
        self.library_dirs = library_dirs
        self.frameworks = frameworks
        self.private_frameworks = private_frameworks
        self.libraries = libraries
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
        path = resolve_path(ins_stack.filename).parent
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
            if self.type == "tool" or self.type == "framework":
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
        self.bridging_headers = [resolve_path(f) for f in self.bridging_headers]

        # resources dir
        self.resources_dir = resolve_path(resources_dir)

        # see if bridging headers exist
        for f in self.bridging_headers:
            if not f.exists():
                raise FileNotFoundError(f'Bridging header "{f}" not found')

        # resolve include dirs
        self.include_dirs = [str(resolve_path(f)) for f in self.include_dirs]

        # resolve framework dirs
        self.framework_dirs = [str(resolve_path(f)) for f in self.framework_dirs]

        # resolve library dirs
        self.library_dirs = [str(resolve_path(f)) for f in self.library_dirs]

        # add default values
        if self.type in default_values:
            for key in default_values[self.type]:
                # add keys in array to array
                self.__dict__[key].extend(default_values[self.type][key])

    @property
    def abbreviated_name(self):
        if len(self.name) >= 3:
            return self.name[:3].upper()
        else:
            return (" " * (3 - len(self.name))) + self.name.upper()
