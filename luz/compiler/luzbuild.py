# module imports
from argparse import Namespace
from atexit import register
from json import loads
from multiprocessing.pool import ThreadPool
from os import makedirs
from pathlib import Path
from platform import platform
from pyclang import CCompiler, SwiftCompiler
from pydeb import Control, Pack
from shutil import copytree, rmtree
from subprocess import getoutput
from threading import Lock
from time import time
from yaml import safe_load

# local imports
from ..common.logger import ask, colors, error, log, log_stdout, remove_log_stdout
from ..common.utils import (
    cmd_in_path,
    get_from_cfg,
    get_from_luzbuild,
    get_luz_storage,
    resolve_path,
    setup_luz_dir,
)
from .modules.modules import assign_module


class LuzBuild:
    def __init__(
        self,
        args: Namespace,
        path_to_file: str = "LuzBuild",
        inherit: object = None,
    ):
        """Parse the luzbuild file.

        :param str path_to_file: The path to the luzbuild file.
        """
        # start
        self.time = time()

        # args
        self.args = args

        # to inherit
        self.to_inherit = inherit

        if self.to_inherit is not None:
            self.passed_config = getattr(self.to_inherit, "passed_config")
        else:
            self.passed_config = {}
            if self.args.meta:
                passed_cfg = list(map(lambda x: x[0].lower(), self.args.meta))
                for n in passed_cfg:
                    spl = n.split("=")
                    self.passed_config[spl[0]] = self.__assign_passed_value(spl[1])

        # path
        self.path = resolve_path(str(path_to_file).split("LuzBuild")[0])

        if self.to_inherit is None:
            # module path
            module_path = resolve_path(resolve_path(__file__).absolute()).parent

            # read default config values
            with open(f"{module_path}/config/defaults.yaml") as f:
                self.defaults = safe_load(f)
        else:
            self.defaults = getattr(self.to_inherit, "defaults")

        # open and parse luzbuild file
        with open(path_to_file) as f:
            self.luzbuild = safe_load(f)

        # exit if failed
        if self.luzbuild is None or self.luzbuild == {}:
            return self.__error_and_exit("Failed to parse luzbuild file.")

        # clean
        if args.clean and self.to_inherit is None:
            rmtree(".luz", ignore_errors=True)

        # dir
        self.dir = setup_luz_dir()

        # remove staging
        if resolve_path(f"{self.dir}/_").exists():
            rmtree(resolve_path(f"{self.dir}/_"))

        # hashlist
        if self.to_inherit is not None:
            self.hashlist = getattr(self.to_inherit, "hashlist")
        else:
            hash_file = resolve_path(f"{self.dir}/hashlist.json")
            # check if hashlist exists
            if hash_file.exists():
                with open(hash_file, "r") as f:
                    self.hashlist = loads(f.read())
            else:
                self.hashlist = {}

        # pool
        self.pool = ThreadPool()

        # register pool close
        register(self.pool.close)

        # lock
        self.lock = Lock()

        # control
        if self.to_inherit is not None:
            self.control = getattr(self.to_inherit, "control")
            self.control_raw = getattr(self.to_inherit, "control_raw")
            self.scripts = getattr(self.to_inherit, "scripts")
        else:
            self.control = None
            self.control_raw = ""
            self.scripts = {}

        # debug
        self.debug = self.__get("debug", "meta.debug")

        # release
        self.release = self.__get("release", "meta.release")

        # fix up
        if self.debug == True and self.release == True:
            self.debug = False
        elif self.debug == False:
            self.release = True

        if self.to_inherit is None:
            if self.debug:
                build = resolve_path(f"{self.dir}/last_build")
                if build.exists():
                    with open(build, "r") as f:
                        self.build_number = int(f.read()) + 1
                else:
                    self.build_number = 1
                with open(build, "w") as f:
                    f.write(str(self.build_number))
        else:
            if self.debug:
                self.build_number = getattr(self.to_inherit, "build_number")

        # storage dir
        self.storage = get_luz_storage()

        # sdk
        self.sdk = self.__get("sdk", "meta.sdk")

        # prefix
        self.prefix = self.__get("prefix", "meta.prefix")

        if self.prefix == "" and platform().startswith("Linux"):
            luz_prefix = resolve_path(f"{self.storage}/toolchain/linux/iphone/bin")
            if not luz_prefix.exists():
                self.__error_and_exit("Running on Linux, and toolchain is not installed.")
            self.prefix = luz_prefix

        # cc
        self.cc = self.__get("cc", "meta.cc")

        # swift
        self.swift = self.__get("swift", "meta.swift")

        # rootless
        self.rootless = self.__get("rootless", "meta.rootless")

        # compression
        self.compression = self.__get("compression", "meta.compression")

        # archs
        self.archs = self.__get("archs", "meta.archs")

        # platform
        self.platform = self.__get("platform", "meta.platform")

        # min version
        self.min_vers = self.__get("min_vers", "meta.minVers")

        # should pack
        self.should_pack = bool(self.__get("should_pack", "meta.pack"))

        # modules
        self.modules = get_from_luzbuild(self, "modules")

        # swift
        self.compile_for_swift = ".swift" in str(self.modules)

        # submodules
        self.submodules = []

        # ensure prefix exists
        if self.prefix is not "":
            self.prefix = resolve_path(self.prefix)
            if not self.prefix.exists():
                return self.__error_and_exit("Specified prefix does not exist.")

        # get git
        self.git = cmd_in_path("git")
        if self.git is None:
            return self.__error_and_exit("Git is needed in order to use Luz.")

        # format cc with prefix
        if self.prefix is not "" and not resolve_path(self.cc).is_relative_to("/"):
            prefix_path = cmd_in_path(f"{self.prefix}/{self.cc}")
            if not prefix_path:
                return self.__error_and_exit(f'C compiler "{self.cc}" not in prefix path.')
            self.cc = prefix_path

        # format swift with prefix
        if self.prefix is not "" and not resolve_path(self.swift).is_relative_to("/"):
            prefix_path = cmd_in_path(f"{self.prefix}/{self.swift}")
            if not prefix_path:
                return self.__error_and_exit(f'Swift compiler "{self.swift}" not in prefix path.')
            self.swift = prefix_path

        # format install_name_tool with prefix
        self.install_name_tool = cmd_in_path(f'{(str(self.prefix) + "/") if self.prefix is not None else ""}install_name_tool')
        if self.install_name_tool is None:
            # fall back to path
            self.install_name_tool = cmd_in_path("install_name_tool")
            if self.install_name_tool is None:
                return self.__error_and_exit("Could not find install_name_tool.")

        # format ldid with prefix
        self.ldid = cmd_in_path(f'{(str(self.prefix) + "/") if self.prefix is not None else ""}ldid')
        if self.ldid is None:
            # fall back to path
            self.ldid = cmd_in_path("ldid")
            if self.ldid is None:
                return self.__error_and_exit("Could not find ldid.")

        # format ld with prefix
        self.ld = cmd_in_path(f'{(str(self.prefix) + "/") if self.prefix is not None else ""}ld')
        if self.ld is None:
            # fall back to path
            self.ld = cmd_in_path("ld")
            if self.ld is None:
                return self.__error_and_exit("Could not find ld.")

        # format ldid with prefix
        self.strip = cmd_in_path(f'{(str(self.prefix) + "/") if self.prefix is not None else ""}strip')
        if self.strip is None:
            # fall back to path
            self.strip = cmd_in_path("strip")
            if self.strip is None:
                return self.__error_and_exit("Could not find strip.")

        # format lipo with prefix
        self.lipo = cmd_in_path(f'{(str(self.prefix) + "/") if self.prefix is not None else ""}lipo')
        if self.lipo is None:
            # fall back to path
            self.lipo = cmd_in_path("lipo")
            if self.lipo is None:
                return self.__error_and_exit("Could not find lipo.")

        # attempt to manually find an sdk
        if self.sdk == "":
            self.sdk = self.__get_sdk()
        else:
            # ensure sdk exists
            self.sdk = resolve_path(self.sdk)
            if not self.sdk.exists():
                if resolve_path(f"{self.storage}/sdks/{self.sdk}").exists():
                    self.sdk = resolve_path(f"{self.storage}/sdks/{self.sdk}")
                else:
                    return self.__error_and_exit("Specified SDK does not exist.")

        # parse modules
        if self.modules is not None:
            # set compiler
            self.c_compiler = CCompiler().set_compiler(self.cc)
            # get modules
            for m in self.modules:
                # get module data
                v = self.modules.get(m)
                # make sure files is a list
                if type(v.get("files")) is not list:
                    v["files"] = [v["files"]]
                # look for swift
                if ".swift" in str(v.get("files")):
                    self.compile_for_swift = True
                    if type(self.swift) is not Path:
                        self.swift = cmd_in_path(self.swift)
                        if self.swift is None:
                            return self.__error_and_exit("Swift compiler not found.")
                        self.swift_compiler = SwiftCompiler().set_compiler(self.swift)
                # assign module
                self.modules[m] = assign_module(v, m, self)
        elif self.modules is None or self.modules == {}:
            if get_from_cfg(self, "submodules") == []:
                return self.__error_and_exit("No modules found in LuzBuild file.")

        # parse luzbuild file
        self.pool.map(lambda x: self.__handle_key(x), self.luzbuild)

        # get submodules
        subproj_results = self.pool.map(lambda x: self.__handle_submodule(x), get_from_cfg(self, "submodules"))
        for result in subproj_results:
            if result is not None:
                self.__error_and_exit(result)

        # read control if it doesn't exist
        if self.control_raw == "":
            control_path = resolve_path(f"{self.path}/control")
            layout_control_path = resolve_path(f"{self.path}/layout/DEBIAN/control")
            if control_path.exists():
                with open(control_path, "r") as f:
                    self.control_raw = f.read()
            elif layout_control_path.exists():
                with open(layout_control_path, "r") as f:
                    self.control_raw = f.read()
            else:
                return self.__error_and_exit("No control file found, and package metadata was not declared in LuzBuild.")
        # parse control
        if self.control is None:
            self.control = Control(self.control_raw)

    def update_hashlist(self, keys):
        """Update the hashlist with a list of keys."""
        self.hashlist.update(keys)

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

    def __get(self, obj_key, def_key):
        """Get a key from either the LuzBuild, inherited object, or default config."""
        if obj_key in self.passed_config:
            return self.passed_config[obj_key]
        elif get_from_luzbuild(self, def_key) is not None:
            return get_from_luzbuild(self, def_key)
        elif self.to_inherit is not None:
            return getattr(self.to_inherit, obj_key)
        else:
            return get_from_cfg(self, def_key)

    def __handle_submodule(self, submodule):
        """Handle a submodule dir.

        :param str submodule: Directory of submodule.
        """
        path = resolve_path(submodule + "/LuzBuild")
        if not path.exists():
            return f'Submodule "{submodule}" does not exist.'
        # get luzbuild
        luzbuild = LuzBuild(args=self.args, path_to_file=path, inherit=self)
        # add to submodules
        self.submodules.append(luzbuild)

    def __handle_key(self, key):
        """Handle a key in the LuzBuild file.

        :param str key: The key to handle.
        """
        key = str(key).lower()
        value = self.luzbuild.get(key)

        # control assignments
        if key == "control" and self.should_pack:
            for c in value:
                v = value.get(c)
                c = str(c).lower()
                # control assignments
                if c in [
                    "name",
                    "id",
                    "depends",
                    "architecture",
                    "version",
                    "maintainer",
                    "description",
                    "section",
                    "author",
                    "icon",
                    "priority",
                    "size",
                    "tags",
                    "replaces",
                    "provides",
                    "conflicts",
                    "installed-size",
                    "depiction",
                    "tag",
                    "package",
                    "sileodepiction",
                ]:
                    if type(v) is str:
                        end = "\n"
                        # id patch
                        if c == "id":
                            self.control_raw += f"Package: {v}{end}"
                        # maintainer
                        elif c == "author" and not "maintainer" in list(self.luzbuild.get("control")):
                            self.control_raw += f"Author: {v}{end}Maintainer: {v}{end}"
                        # debug version patch
                        elif c == "version" and self.debug:
                            self.control_raw += f"Version: {v}-{self.build_number}+debug{end}"
                        # author
                        elif c == "maintainer" and not "author" in list(self.luzbuild.get("control")):
                            self.control_raw += f"Author: {v}{end}Maintainer: {v}{end}"
                        # sileodepiction patch
                        elif c == "sileodepiction":
                            self.control_raw += f"SileoDepiction: {v}{end}"
                        # installed-size patch
                        elif c == "installed-size":
                            self.control_raw += f"Installed-Size: {v}{end}"
                        # other values
                        else:
                            self.control_raw += f"{c.capitalize()}: {v}{end}"

        # scripts
        if key == "scripts" and self.should_pack:
            for script in value:
                if script in ["preinst", "postinst", "prerm", "postrm"]:
                    v = value.get(script)
                    if type(v) == list:
                        script_raw = "\n".join(v)
                    else:
                        script_raw = v
                    self.scripts[script] = script_raw

    def __error_and_exit(self, msg):
        """Print an error and exit.

        :param str msg: The error to print.
        """
        if self.to_inherit is not None:
            return msg
        else:
            error(msg)
            exit(1)

    def __xcrun(self):
        xcrun = cmd_in_path("xcrun")
        if xcrun is None:
            return self.__error_and_exit("xcrun not found.")
        else:
            log_stdout("Finding an SDK...")
            sdkA = getoutput(f"{xcrun} --show-sdk-path --sdk {self.platform}").split("\n")[-1]
            if sdkA == "" or not sdkA.startswith("/"):
                return self.__error_and_exit("Could not find any SDKs. Please specify one manually.")
            remove_log_stdout("Finding an SDK...")
            self.sdk = sdkA
        return resolve_path(self.sdk)

    def __get_sdk(self):
        """Get an SDK from Xcode using xcrun."""
        sdks_path = resolve_path(f"{self.storage}/sdks")
        if sdks_path.exists():
            # get valid sdk paths that match the target platform
            valid_sdks = list(filter(lambda x: self.platform.lower() in x.name.lower(), sdks_path.iterdir()))
            # get the sdk that closest matches the minimum version
            if len(valid_sdks) == 0:
                return self.__xcrun()
            else:
                minimum = min(valid_sdks, key=lambda x: abs(float(str(x.name).lower().replace(self.platform.lower(), "").replace(".sdk", "")) - float(self.min_vers)))
                return minimum

        else:
            return self.__xcrun()

    def __pack(self):
        """Pack up the .deb file."""
        log_stdout("Packing deb file...", self.lock)
        # layout
        layout_path = resolve_path("layout")
        if layout_path.exists():
            copytree(layout_path, f"{self.dir}/_", dirs_exist_ok=True)
        # submodule layout paths
        for submodule in self.submodules:
            layout_path = resolve_path(f"{submodule.path}/layout")
            if layout_path.exists():
                copytree(layout_path, f"{self.dir}/_", dirs_exist_ok=True)
        # scripts
        for script in self.scripts:
            with open(f"{self.dir}/_/DEBIAN/{script}", "w") as f:
                f.write(self.scripts[script])
        # pack
        Pack(
            resolve_path(f"{self.dir}/_"),
            algorithm=self.compression,
            outdir="packages/",
        )
        remove_log_stdout("Packing deb file...", self.lock)

    def build(self):
        """Build the project."""
        # compile results
        if self.modules != None:
            compile_results = self.pool.map(lambda x: x.compile(), self.modules.values())
            for result in compile_results:
                if result is not None:
                    return result

        # compile submodules
        if self.submodules != []:
            compile_results = self.pool.map(lambda x: x.build(), self.submodules)
            for result in compile_results:
                if result is not None:
                    return result

    def build_and_pack(self):
        """Build and pack the project."""
        # build
        build_results = self.build()
        if build_results is not None:
            self.__error_and_exit(build_results)
        if self.should_pack:
            # make staging dirs
            if not resolve_path(f"{self.dir}/_/DEBIAN").exists():
                makedirs(f"{self.dir}/_/DEBIAN")
            # write control
            with open(f"{self.dir}/_/DEBIAN/control", "w") as f:
                f.write(self.control_raw)
            self.__pack()
        with open(resolve_path(f"{self.dir}/hashlist.json"), "w") as f:
            f.write(str(self.hashlist).replace("'", '"'))

        log(f"Done in {round(time() - self.time, 2)} seconds.")
