# Copyright (c) 2026 Jaidan Arenas
"""Project loader and build entrypoint behind the public :class:`Luz` API."""

# module imports
from argparse import Namespace
from atexit import register
from concurrent.futures import ThreadPoolExecutor
from email.parser import Parser
from importlib.util import module_from_spec, spec_from_file_location
from json import dump, loads
from multiprocessing import Lock
from os import makedirs
from shutil import copytree, rmtree
from subprocess import run
from stat import S_IXGRP, S_IXOTH, S_IXUSR
from sys import modules
from time import time

# local imports
from ..build.assign import assign
from ..common.logger import error, log, warn
from ..common.time import Ctime
from ..common.deb import build_deb
from ..common.utils import CMD, resolve_path, setup_luz_dir
from ..common import cfg

# import components
from .components.control import Control
from .components.meta import Meta


def _control_list(value):
    """Convert a Debian relationship field into values accepted by Control.

    Manual control files store relationship entries as comma-separated text;
    Luz's ``Control`` API stores them as lists before serializing them again.
    """
    return [item.strip() for item in value.split(",") if item.strip()] if value else []


class Luz:
    """Load a ``luzconf.py`` and coordinate its build, package, and install.

    Most projects never instantiate this class inside their configuration: the
    ``luz`` command loads the file and creates it.  It remains public for editor
    integration, embedding Luz in another Python tool, and test projects.  The
    configuration module may expose ``meta``, ``control``, ``modules``,
    ``scripts``, and ``submodules`` variables using the public configuration
    classes.

    ``build_project()`` compiles each module, stages package content, creates a
    ``.deb`` when :attr:`Meta.pack` is true, and performs remote installation only
    when the CLI requested it for a physical iOS target.
    """

    def __init__(self, file_path: str = "luzconf.py", args: Namespace = None, inherit=None):
        """Load a project configuration without starting its build.

        Args:
            file_path: Configuration file to load.  Relative paths are
                resolved from the current working directory; project-relative
                paths inside ``Module`` and ``Script`` are then resolved from
                the configuration file's directory.
            args: Optional CLI argument namespace.  Luz reads ``clean``,
                ``install``, ``funny_time``, and ``meta`` overrides from it.
                Pass ``None`` when embedding Luz programmatically.
            inherit: Parent :class:`Luz` instance used while loading a
                ``Submodule``.  It shares build timing, locks, command
                execution, and unspecified meta values with the parent.

        Raises:
            FileNotFoundError: If ``file_path`` does not exist.
            ValueError: If package metadata is required but neither a
                ``Control`` declaration nor a manual control file is present.
        """
        cfg.inherit = inherit
        if inherit is None:
            # Module construction changes into the project directory. Keep
            # this path absolute so clean builds always recreate the same
            # project's .luz directory.
            cfg.luzconf_path = resolve_path(file_path).absolute()

        if inherit is None:
            # handle passed meta config
            if args is not None and args.meta is not None:
                passed = {}
                for key in args.meta:
                    spl = key[0].split("=")
                    passed[spl[0]] = self.__assign_passed_value(spl[1])
                cfg.passed = passed

        if inherit is None:
            self.now = time()
        else:
            self.now = inherit.now
        # ensure that the file exists
        if not resolve_path(file_path).exists():
            raise FileNotFoundError(f"File {file_path} not found")

        # Keep the project root absolute because Module() changes the working
        # directory while loading a configuration file.
        self.path = resolve_path(file_path).absolute().parent if inherit is None else inherit.path

        # nuke build dir if clean
        if args is not None and args.clean:
            rmtree(resolve_path(file_path).absolute().parent / ".luz", ignore_errors=True)

        # funnytime
        self.funny_time = args.funny_time if args is not None else False

        # clean
        self.clean = args.clean if args is not None else False

        # install
        self.install = args.install if args is not None else False

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

        # inherit values
        if inherit is not None:
            # inherit meta
            for key, value in self.meta.__dict__.items():
                if value == "" or value is None or value == []:
                    setattr(self.meta, key, getattr(inherit.meta, key))

        # pool
        # An explicit jobs value limits module scheduling globally. Otherwise
        # preserve Luz's original high-throughput outer scheduler.
        self.pool = ThreadPoolExecutor(
            max_workers=min(20, self.meta.jobs) if self.meta.jobs is not None else 20
        ) if inherit is None else inherit.pool

        # lock
        self.lock = Lock() if inherit is None else inherit.lock

        # compilers
        if inherit is not None:
            self.cmd = inherit.cmd
        else:
            self.cmd = CMD(lock=self.lock, show_messages=self.meta.messages, jobs=self.meta.jobs)

        # control
        self.control = getattr(self.raw, "control", None if inherit is None else inherit.control)

        # read manual control
        if self.control is None and self.meta.pack:
            dot_path = resolve_path(f"{self.path}/control")
            layout_path = resolve_path(f"{self.path}/layout/DEBIAN/control")
            if dot_path.exists():
                with open(dot_path, "r") as file:
                    control = Parser().parsestr(file.read())
            elif layout_path.exists():
                with open(layout_path, "r") as file:
                    control = Parser().parsestr(file.read())
            else:
                control = None
            # assign values
            if control is not None:
                # add values to control
                warn("Using manual control file. Please use the Control class to create a control file.")
                self.control = Control(
                    id=control["Package"],
                    version=control["Version"],
                    maintainer=control["Maintainer"],
                    architecture=control["Architecture"],
                    description=control.get("Description"),
                    depends=_control_list(control.get("Depends")),
                    section=control.get("Section"),
                    priority=control.get("Priority"),
                    homepage=control.get("Homepage"),
                    conflicts=_control_list(control.get("Conflicts")),
                    replaces=_control_list(control.get("Replaces")),
                    provides=_control_list(control.get("Provides")),
                    recommends=_control_list(control.get("Recommends")),
                    suggests=_control_list(control.get("Suggests")),
                    breaks=_control_list(control.get("Breaks")),
                    enhances=_control_list(control.get("Enhances")),
                    pre_depends=_control_list(control.get("Pre-Depends")),
                    essential=control.get("Essential", "").lower() == "yes",
                    original_maintainer=control.get("Original-Maintainer"),
                    uploaders=_control_list(control.get("Uploaders")),
                )
            else:
                raise ValueError("No control file found. Please create a control file or use the Control class to create a control file.")

        # scripts
        self.scripts = getattr(self.raw, "scripts", [])

        # modules
        self.modules = getattr(self.raw, "modules", [])

        # submodules
        self.submodules = getattr(self.raw, "submodules", [])

        # A project without control metadata cannot produce a Debian package,
        # but it can still compile a local macOS command-line tool.
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
                with open(hash_file, "r") as file:
                    self.build_info = loads(file.read())
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

        return Luz(f"{submodule.path}/luzconf.py", inherit=self if submodule.inherit else None)

    def update_hashlist(self, keys):
        """Merge source-state hashes into the incremental-build cache.

        Args:
            keys: Mapping of cache keys to content/build hashes.  This is an
                extension point for custom builders; normal ``Module`` builds
                update the cache automatically.
        """
        self.build_info["hashlist"].update(keys)

    def __pack(self):
        """Package the project."""
        # deb file name
        deb_file_name = f"{self.control.id}_{self.control.version}_{self.control.architecture}.deb"
        # log
        if self.path.absolute() == self.path.cwd().absolute():
            dir_to_log = "."
        else:
            dir_to_log = str(self.path.absolute()).replace(str(self.path.cwd().absolute()), ".")
        log(f"Packing to '{dir_to_log}/packages/{deb_file_name}'...", "📦")
        # layout
        layout_path = resolve_path("layout")
        if layout_path.exists():
            copytree(layout_path, self.meta.root_dir, dirs_exist_ok=True)
        # submodule layout paths
        for submodule in self.submodules:
            layout_path = resolve_path(f"{submodule.path}/layout")
            if layout_path.exists():
                copytree(layout_path, self.meta.root_dir, dirs_exist_ok=True)
        # makedirs
        makedirs(f"{self.meta.staging_dir}/DEBIAN", exist_ok=True)
        # add control
        with open(f"{self.meta.staging_dir}/DEBIAN/control", "w") as file:
            file.write(self.control.__str__())
        # scripts
        for script in self.scripts:
            script_path = resolve_path(f"{self.meta.staging_dir}/DEBIAN/{script.type}")
            with open(script_path, "w") as file:
                file.write(script.content)
            script_path.chmod(script_path.stat().st_mode | S_IXUSR | S_IXGRP | S_IXOTH)
        # pack
        build_deb(
            self.meta.staging_dir,
            self.path / "packages" / deb_file_name,
            compression=self.meta.compression,
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
        """Compile, optionally package, and optionally install the project.

        Compilation errors are raised after module workers finish.  When
        :attr:`Meta.pack` is true, the resulting Debian archive is written to
        ``<project>/packages`` using the control package id, version, and
        architecture.  CLI-triggered installation copies that archive over
        SSH and executes ``dpkg -i`` on a physical iOS device; simulator and
        macOS builds deliberately do not support package installation.

        Raises:
            Exception: If a module or submodule build fails.
        """
        # Start with a clean package staging tree before modules copy their
        # outputs into it. Clearing it in __pack() would erase every staged
        # dylib, framework, and resource immediately before archiving.
        if self.meta.pack:
            rmtree(self.meta.staging_dir, ignore_errors=True)
            makedirs(self.meta.staging_dir, exist_ok=True)

        # assign modules
        build_results = self.__build()

        if build_results is not None:
            raise Exception(build_results)

        if self.meta.pack:
            self.__pack()

        with open(resolve_path(f"{self.build_dir}/build_info.json"), "w") as file:
            dump(self.build_info, file)

        t = time() - self.now
        log(f"Build completed in {round(t, 2)} seconds.{f' ({Ctime(t).get_random()})' if self.funny_time else ''}")
        if self.install:
            if not self.meta.is_device:
                error("Installation is currently not supported for platforms other than iOS.")
                exit(1)
            # deb file name
            deb_file_name = f"{self.control.id}_{self.control.version}_{self.control.architecture}.deb"
            # log
            log(f"Installing...")
            # full path to package
            package_path = self.path.absolute() / "packages" / deb_file_name
            # copy package
            self.cmd.exec_no_output(f"scp -P {self.meta.install_port} {package_path} {self.meta.install_user}@{self.meta.install_ip}:/tmp/luz.deb")
            # ssh in and install package
            self.cmd.exec_output(f"ssh {self.meta.install_user}@{self.meta.install_ip} -p {self.meta.install_port} 'dpkg -i /tmp/luz.deb && rm -f /tmp/luz.deb'")
            # log
            log(f"Installed!")
