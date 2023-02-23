# module imports
from typing import Union

# local imports
from ...common.utils import resolve_path

class Module():
    def __init__(self,
        files: Union[list, str],
        name: str,
        module_type: str = "tweak",
        install_dir: str = "",
        c_flags: str = "",
        swift_flags: str = "",
        optimization: int = 0,
        warnings: str = "-Wall",
        ent_flag: str = "-S",
        ent_file: str = "",
        filter: dict = {
            "bundles": [
                "com.apple.SpringBoard"
            ]
        },
        use_arc: bool = True,
        only_compile_changed: bool = True,
        bridging_headers: list = [],
        frameworks: list = [],
        private_frameworks: list = [],
        libraries: list = []
    ):
        """Initialize Module
        
        Args:
            files (Union[list, str]): Files to compile
            name (str): Name of module
            module_type (str, optional): Type of module (default: tweak)
            install_dir (str, optional): Directory to install the module to
            c_flags (str, optional): C flags
            swift_flags (str, optional): Swift flags
            optimization (int, optional): Optimization level (default: 0)
            warnings (str, optional): Warnings (default: -Wall)
            ent_flag (str, optional): Entitlements flag (default: -S)
            ent_file (str, optional): Entitlements file
            filter (dict, optional): Filter
            use_arc (bool, optional): Use ARC (default: True)
            only_compile_changed (bool, optional): Only compile changed files (default: True)
            bridging_headers (list, optional): Bridging headers
            frameworks (list, optional): Frameworks to link
            private_frameworks (list, optional): Private frameworks to link
            libraries (list, optional): Libraries to link
        """
        
        # assign variables
        self.type = module_type
        self.name = name
        self.files = files
        self.install_dir = install_dir
        self.c_flags = c_flags
        self.swift_flags = swift_flags
        self.optimization = optimization
        self.warnings = warnings
        self.ent_flag = ent_flag
        self.ent_file = ent_file
        self.filter = filter
        self.use_arc = use_arc
        self.only_compile_changed = only_compile_changed
        self.bridging_headers = bridging_headers
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
        self.files = [resolve_path(f) for f in self.files]

        # see if files exist
        for f in self.files:
            if not f.exists():
                raise FileNotFoundError(f'File "{f}" not found')

        # resolve bridging headers
        self.bridging_headers = [resolve_path(f) for f in self.bridging_headers]

        # see if bridging headers exist
        for f in self.bridging_headers:
            if not f.exists():
                raise FileNotFoundError(f'Bridging header "{f}" not found')
        