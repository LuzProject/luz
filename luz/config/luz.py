# module imports
from argparse import Namespace
from atexit import register
from concurrent.futures import ThreadPoolExecutor
from importlib.util import module_from_spec, spec_from_file_location
from json import dump, loads
from multiprocessing import Lock
from os import makedirs
from pyclang import CCompiler, SwiftCompiler
from pydeb import Control as pControl, Pack
from shutil import copytree, rmtree
from sys import modules
from time import time

# local imports
from ..build.assign import assign
from ..common.logger import log, warn
from ..common.time import Ctime
from ..common.utils import resolve_path, setup_luz_dir

# import components
from .components.control import Control
from .components.meta import Meta


class Luz:
    def __init__(self, file_path: str = "luz.py", args: Namespace = None, inherit=None):
        """Initialize Luz

        :param str file_path: Path to luz.py
        """
        if inherit is None:
            self.now = time()
        else:
            self.now = inherit.now
        # ensure that the file exists
        if not resolve_path(file_path).exists():
            raise FileNotFoundError(f"File {file_path} not found")

        # path
        self.path = resolve_path(file_path).parent

        # nuke build dir if clean
        if args is not None and args.clean:
            rmtree(resolve_path(f"{self.path}/.luz").absolute(), ignore_errors=True)

        # funnytime
        self.funny_time = args.funny_time if args is not None else False

        # clean
        self.clean = args.clean if args is not None else False

        # convert absolute file path to python import path
        spec = spec_from_file_location("build", resolve_path(file_path).absolute())
        luz = module_from_spec(spec)
        modules["build"] = luz
        spec.loader.exec_module(luz)

        # remove pycache
        rmtree(resolve_path(f"{self.path}/__pycache__").absolute(), ignore_errors=True)

        # import file
        self.raw = luz

        # meta
        self.meta = getattr(self.raw, "meta", Meta() if inherit is None else inherit.meta)

        if inherit is not None:
            self.passed_config = getattr(inherit, "passed_config")
        else:
            self.passed_config = {}
            if args is not None and args.meta is not None:
                passed_cfg = list(map(lambda x: x[0].lower(), args.meta))
                for n in passed_cfg:
                    spl = n.split("=")
                    self.passed_config[spl[0]] = self.__assign_passed_value(spl[1])

        # inherit values
        if inherit is not None:
            # inherit meta
            for key, value in self.meta.__dict__.items():
                if value == "" or value is None or value == []:
                    setattr(self.meta, key, getattr(inherit.meta, key))

        # handle passed config
        if self.passed_config != {}:
            for key, value in self.passed_config.items():
                setattr(self.meta, key, value)
        
        # rootless
        if self.meta.rootless and self.meta.platform != "iphoneos":
            warn("Rootless is only supported on iOS. Overriding...")
            self.meta.rootless = False

        # pool
        self.pool = ThreadPoolExecutor(max_workers=20) if inherit is None else inherit.pool

        # lock
        self.lock = Lock() if inherit is None else inherit.lock

        # compilers
        if inherit is not None:
            if inherit.meta.cc != self.meta.cc:
                self.c_compiler = CCompiler(lock=self.lock).set_compiler(self.meta.cc)
            else:
                self.c_compiler = inherit.c_compiler

            if inherit.meta.swift != self.meta.swift:
                self.swift_compiler = SwiftCompiler(lock=self.lock).set_compiler(self.meta.swift)
            else:
                self.swift_compiler = inherit.swift_compiler
        else:
            self.c_compiler = CCompiler(lock=self.lock).set_compiler(self.meta.cc)
            self.swift_compiler = SwiftCompiler(lock=self.lock).set_compiler(self.meta.swift)

        # control
        self.control = getattr(self.raw, "control", None if inherit is None else inherit.control)

        # read manual control
        if self.control is None and self.meta.pack:
            dot_path = resolve_path(f"{self.path}/control")
            layout_path = resolve_path(f"{self.path}/layout/DEBIAN/control")
            if dot_path.exists():
                with open(dot_path, "r") as f:
                    control = pControl(f.read())
            elif layout_path.exists():
                with open(layout_path, "r") as f:
                    control = pControl(f.read())
            else:
                control = None
            # assign values
            if control is not None:
                # add values to control
                warn("Using manual control file. Please use the Control class to create a control file.")
                self.control = Control(
                    id=control.package,
                    version=control.version,
                    maintainer=control.maintainer,
                    architecture=control.architecture,
                    name=control.name,
                    description=control.description,
                    author=control.author,
                    depends=control.depends,
                    section=control.section,
                )
            else:
                raise ValueError("No control file found. Please create a control file or use the Control class to create a control file.")

        # modules
        self.modules = getattr(self.raw, "modules", [])

        # submodules
        self.submodules = getattr(self.raw, "submodules", [])

        # pack
        if self.control is None:
            self.meta.pack = False

        # luz dir
        self.build_dir = setup_luz_dir() if inherit is None else inherit.build_dir

        # initialize atexit
        register(self.pool.shutdown)

        # hashlist
        if inherit is not None:
            self.build_info = getattr(inherit, "build_info")
        else:
            hash_file = resolve_path(f"{self.build_dir}/build_info.json")
            # check if hashlist exists
            if hash_file.exists():
                with open(hash_file, "r") as f:
                    self.build_info = loads(f.read())
            else:
                self.build_info = {}

        if self.meta.debug and self.meta.pack:
            # get build number
            if inherit is None:
                if self.build_info != {} and "build_number" in self.build_info:
                    self.build_info["build_number"] += 1
                    self.build_number = self.build_info["build_number"]
                else:
                    self.build_info["build_number"] = 1
                    self.build_number = 1
                # update control with build number
                self.control.version = f"{self.control.version}-{self.build_number}+debug"
                self.control.raw = self.control.__str__()
            else:
                self.build_number = getattr(inherit, "build_number")

        # assign submodules
        submodules = self.pool.map(self.__assign_submodule, self.submodules)
        self.submodules = submodules

    def __assign_passed_value(self, value):
        """Assign a key from the passed config."""
        if value.lower() == "true" or value.lower() == "false":
            return value.lower() == "true"
        elif value.isdigit():
            return int(value)
        elif value.startswith("[") and value.endswith("]"):
            arr = []
            for v in value[1:-1].split(","):
                arr.append(self.__assign_passed_value(v.replace("'", "").replace('"', "")))
            return arr
        else:
            return value

    def __assign_submodule(self, submodule):
        """Assign submodule."""
        if str(submodule.path).startswith("./"):
            submodule.path = str(submodule.path)[2:]

        if not str(submodule.path).startswith("/"):
            submodule.path = f"{self.path}/{submodule.path}"

        return Luz(f"{submodule.path}/luz.py", inherit=self if submodule.inherit else None)

    def update_hashlist(self, keys):
        """Update the hashlist with a list of keys."""
        self.build_info["hashlist"].update(keys)

    def __pack(self):
        """Package the project."""
        # log
        log("Packaging...", "📦")
        # layout
        layout_path = resolve_path("layout")
        if layout_path.exists():
            copytree(layout_path, f"{self.build_dir}/_", dirs_exist_ok=True)
        # submodule layout paths
        for submodule in self.submodules:
            layout_path = resolve_path(f"{submodule.path}/layout")
            if layout_path.exists():
                copytree(layout_path, f"{self.build_dir}/_", dirs_exist_ok=True)
        # makedirs
        makedirs(f"{self.build_dir}/_/DEBIAN", exist_ok=True)
        # add control
        with open(f"{self.build_dir}/_/DEBIAN/control", "w") as f:
            f.write(self.control.raw)
        # pack
        Pack(
            resolve_path(f"{self.build_dir}/_"),
            algorithm=self.meta.compression,
            outdir="packages/",
        )

    def __build(self):
        """Build the project."""
        # assign modules
        mod_map = [assign(m, self) for m in self.modules]

        # build modules
        results = self.pool.map(lambda m: m.compile(), mod_map)
        for result in results:
            if result is not None:
                return result

        # submodule results
        submodule_results = self.pool.map(lambda s: s.__build(), self.submodules)
        for result in submodule_results:
            if result is not None:
                return result

    def build_project(self):
        """Build the project."""
        # assign modules
        build_results = self.__build()

        if build_results is not None:
            raise Exception(build_results)

        if self.meta.pack:
            self.__pack()

        with open(resolve_path(f"{self.build_dir}/build_info.json"), "w") as f:
            dump(self.build_info, f)

        t = time() - self.now
        log(f"Build completed in {round(t, 2)} seconds.{f' ({Ctime(t).get_random()})' if self.funny_time else ''}")
