# module imports
from inspect import stack
from typing import Union

# local imports
from ...common.utils import resolve_path

class Module():
    def __init__(self,
        files: Union[list, str],
        name: str,
        type: str = "tweak",
        install_name: str = "",
        install_dir: str = "",
        c_flags: str = "",
        swift_flags: str = "",
        optimization: int = 0,
        warnings: str = "-Wall",
        codesign_flags: str = "-S",
        filter: dict = {
            "bundles": [
                "com.apple.SpringBoard"
            ]
        },
        use_arc: bool = True,
        only_compile_changed: bool = True,
        bridging_headers: list = [],
        include_dirs: list = [],
        framework_dirs: list = [],
        library_dirs: list = [],
        frameworks: list = [],
        private_frameworks: list = [],
        libraries: list = []
    ):
        """Initialize Module
        
        Args:
            files (Union[list, str]): Files to compile
            name (str): Name of module
            type (str, optional): Type of module (default: tweak)
            install_name (str, optional): Name to install the module as (defaults to the module name)
            install_dir (str, optional): Directory to install the module to
            c_flags (str, optional): C flags
            swift_flags (str, optional): Swift flags
            optimization (int, optional): Optimization level (default: 0)
            warnings (str, optional): Warnings (default: -Wall)
            codesign_flags (str, optional): Entitlements flag (default: -S)
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
        self.install_name =  install_name
        self.install_dir = resolve_path(install_dir) if install_dir != "" else None
        self.c_flags = c_flags
        self.swift_flags = swift_flags
        self.optimization = optimization
        self.warnings = warnings
        self.codesign_flags = codesign_flags
        self.filter = filter
        self.use_arc = use_arc
        self.only_compile_changed = only_compile_changed
        self.bridging_headers = bridging_headers
        self.include_dirs = include_dirs
        self.framework_dirs = framework_dirs
        self.library_dirs = library_dirs
        self.frameworks = frameworks
        self.private_frameworks = private_frameworks
        self.libraries = libraries

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
        b_files = [resolve_path(f) for f in self.files]
        self.files = []

        # stack
        ins_stack = stack()[1]
        path = resolve_path(ins_stack.filename).parent

        # see if files exist
        for f in b_files:
            # check if is list
            if isinstance(f, list):
                for ff in f:
                    if not str(ff).startswith("/"):
                        ff = path / ff
                    if not ff.exists():
                        raise FileNotFoundError(f'File "{ff}" not found')
                    self.files.append(ff)
            else:
                if not str(f).startswith("/"):
                    f = path / f
                if not f.exists():
                    raise FileNotFoundError(f'File "{f}" not found')
                self.files.append(f)

        # fix install name
        if self.install_name == "":
            if self.type == "tool":
                self.install_name = self.name
            else:
                self.install_name = f"{self.name}.dylib"

        # resolve bridging headers
        self.bridging_headers = [resolve_path(f) for f in self.bridging_headers]

        # see if bridging headers exist
        for f in self.bridging_headers:
            if not f.exists():
                raise FileNotFoundError(f'Bridging header "{f}" not found')

        # resolve include dirs
        self.include_dirs = [resolve_path(f) for f in self.include_dirs]

        # resolve framework dirs
        self.framework_dirs = [resolve_path(f) for f in self.framework_dirs]

        # resolve library dirs
        self.library_dirs = [resolve_path(f) for f in self.library_dirs]
        