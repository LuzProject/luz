# module imports
from os import makedirs
from subprocess import check_output

# local imports
from ..deps import clone_headers, clone_libraries, logos
from ...common.logger import log, log_stdout, error, remove_log_stdout
from ...common.utils import get_from_cfg, get_from_default, get_hash, resolve_path


def get_safe(module: dict, key: str, default: str = None) -> str:
    """Gets a key from a dict safely.

    :param dict module: The dict to get the key from.
    :param str key: The key to get.
    :param str default: The default value to return if the key is not found.
    :return: The value of the key.
    """
    return module.get(key) if module.get(key) is not None else default


class Module:
    def __init__(self, module: dict, key: str, luzbuild):
        """Module superclass.

        :param dict module: Module dictionary to build
        :param str key: Module key name
        :param LuzBuild luzbuild: Luzbuild class
        """
        # luzbuild
        self.luzbuild = luzbuild

        # dir
        self.dir = luzbuild.dir

        # stage dir
        self.stage_dir = resolve_path(f"{self.dir}/_")

        # type
        self.type = get_from_cfg(luzbuild, f"modules.{key}.type", "modules.defaultType")

        # allow for 'prefs' module type
        if self.type == "prefs":
            self.type == "preferences"

        # c_flags
        self.c_flags = get_from_cfg(luzbuild, f"modules.{key}.cflags", f"modules.types.{self.type}.cflags")

        # swift_flags
        self.swift_flags = get_from_cfg(luzbuild, f"modules.{key}.swiftflags", f"modules.types.{self.type}.swiftflags")

        # optimization
        self.optimization = get_from_cfg(luzbuild, f"modules.{key}.optimization", f"modules.types.{self.type}.optimization")

        # warnings
        self.warnings = get_from_cfg(luzbuild, f"modules.{key}.warnings", f"modules.types.{self.type}.warnings")

        # entitlement flag
        self.entflag = get_from_cfg(luzbuild, f"modules.{key}.entflag", f"modules.types.{self.type}.entflag")

        # entitlement file
        self.entfile = get_from_cfg(luzbuild, f"modules.{key}.entfile", f"modules.types.{self.type}.entfile")

        # process
        self.filter = get_from_cfg(luzbuild, f"modules.{key}.filter", f"modules.types.{self.type}.filter")

        # install_dir
        self.install_dir = get_safe(module, "installDir", None)

        # name
        self.name = key

        # bridging headers
        self.bridging_headers = ""

        # frameworks
        self.frameworks = ""

        # private frameworks
        self.private_frameworks = ""

        # libraries
        self.libraries = ""

        # library files dir
        self.library_dirs = f"-L{clone_libraries(luzbuild)}"

        # framework files dir
        self.framework_dirs = f""

        files = module.get("files") if type(module.get("files")) is list else [module.get("files")]

        # add swift libs
        if ".swift" in " ".join(files):
            self.library_dirs += f" -L/usr/lib/swift -L{self.luzbuild.sdk}/usr/lib/swift"

        # include
        self.include = f"-I{clone_headers(luzbuild)}"

        # use arc
        self.arc = bool(get_from_cfg(luzbuild, f"modules.{key}.useArc", f"modules.types.{self.type}.useArc"))

        # only compile changes
        self.only_compile_changed = bool(get_from_cfg(luzbuild, f"modules.{key}.onlyCompileChanged", f"modules.types.{self.type}.onlyCompileChanged"))

        # ensure files are defined
        if module.get("files") is None or module.get("files") is [] or module.get("files") is "":
            error(f'No files specified for module "{self.name}".')
            exit(1)

        # define default values
        bridging_headersD = list(get_from_cfg(luzbuild, f"modules.{key}.bridgingHeaders", f"modules.types.{self.type}.bridgingHeaders"))
        frameworksD = list(get_from_default(luzbuild, f"modules.types.{self.type}.frameworks"))
        private_frameworksD = list(get_from_default(luzbuild, f"modules.types.{self.type}.privateFrameworks"))
        librariesD = list(get_from_default(luzbuild, f"modules.types.{self.type}.libraries"))

        # add bridging headers
        bridging_headers = get_safe(module, "bridgingHeaders", [])
        # default frameworks first
        if bridging_headersD != []:
            for bridging_header in bridging_headers:
                self.bridging_headers += f" -import-objc-header {bridging_header}"
        if bridging_headers != []:
            for bridging_header in bridging_headers:
                if not bridging_header.startswith("/"):
                    bridging_header = f"{self.luzbuild.path}/{bridging_header}"
                self.bridging_headers += f" -import-objc-header {bridging_header}"

        # add module frameworks
        frameworks = get_safe(module, "frameworks", [])
        # default frameworks first
        if frameworksD != []:
            for framework in frameworksD:
                self.frameworks += f" -framework {framework}"
        if frameworks != []:
            for framework in frameworks:
                self.frameworks += f" -framework {framework}"

        # add module private frameworks
        private_frameworks = get_safe(module, "privateFrameworks", [])
        # default frameworks first
        if private_frameworksD != []:
            for framework in private_frameworksD:
                self.private_frameworks += f" -framework {framework}"
        if private_frameworks != []:
            for framework in private_frameworks:
                self.private_frameworks += f" -framework {framework}"

        # add module libraries
        libraries = get_safe(module, "libraries", [])
        # default frameworks first
        if librariesD != []:
            for library in librariesD:
                self.libraries += f" -l{library}"
        if libraries != []:
            for library in libraries:
                self.libraries += f" -l{library}"

        # add module include directories
        include = get_safe(module, "include", [])
        if include != []:
            for include in include:
                self.include += f" -I{include}"

        # xcode sdks dont include private frameworks
        if self.private_frameworks != "" and str(self.luzbuild.sdk).startswith("/Applications"):
            error(f"No SDK specified. Xcode will be used, and private frameworks will not be found.")
            exit(1)
        else:
            self.framework_dirs = f"-F{self.luzbuild.sdk}/System/Library/PrivateFrameworks"

        # dirs
        self.obj_dir = resolve_path(f"{self.dir}/obj/{self.name}")
        self.dylib_dir = resolve_path(f"{self.dir}/dylib/{self.name}")
        self.logos_dir = resolve_path(f"{self.dir}/logos-processed")
        self.bin_dir = resolve_path(f"{self.dir}/bin/{self.name}")

        # hash files
        files = module.get("files") if type(module.get("files")) is list else [module.get("files")]
        self.files = self.hash_files(files, "executable" if self.type == "tool" else "dylib", True if self.type == "tweak" else False)

    def hash_files(self, files, compile_type: str = "dylib", run_logos: bool = False):
        """Hash source files, and check if their objects exist.

        :param list files: The list of files to hash.
        :param str type: The type of files to hash.
        """
        # make dirs
        if not self.obj_dir.exists():
            makedirs(self.obj_dir, exist_ok=True)

        files_to_compile = []

        # changed files
        changed = []
        # new hashes
        new_hashes = {}
        # arch count
        arch_count = len(self.luzbuild.archs)
        # file path formatting
        for file in files:
            if not file.startswith("/"):
                file = f"{self.luzbuild.path}/{file}"
            file_path = resolve_path(file)
            if type(file_path) is list:
                for f in file_path:
                    files_to_compile.append(f)
            else:
                files_to_compile.append(file_path)

        # dylib
        if compile_type == "dylib":
            if not self.dylib_dir.exists():
                makedirs(self.dylib_dir, exist_ok=True)
        # executable
        elif compile_type == "executable":
            if not self.bin_dir.exists():
                makedirs(self.bin_dir, exist_ok=True)

        # loop files
        for file in files_to_compile:
            # get file hash
            fhash = self.luzbuild.hashlist.get(str(file))
            new_hash = get_hash(file)
            if fhash is None:
                changed.append(file)
            elif fhash == new_hash:
                # variables
                object_paths = resolve_path(f"{self.dir}/obj/{self.name}/*/{file.name}*-*.o")
                if compile_type == "dylib":
                    dylib_paths = resolve_path(f"{self.dir}/obj/{self.name}/*/{self.name}.dylib")
                elif compile_type == "executable":
                    dylib_paths = resolve_path(f"{self.dir}/obj/{self.name}/*/{self.name}")
                if len(object_paths) < arch_count or len(dylib_paths) < arch_count:
                    changed.append(file)
            elif fhash != new_hash:
                changed.append(file)
            # add to new hashes
            new_hashes[str(file)] = new_hash

        # hashes
        self.luzbuild.update_hashlist(new_hashes)

        # files list
        files = changed if self.only_compile_changed else files_to_compile

        # handle files not needing compilation
        if len(files) == 0:
            self.log(f'Nothing to compile for module "{self.name}".')
            return []

        files = files_to_compile

        # use logos files if necessary
        if run_logos and filter(lambda x: ".x" in x, files) != []:
            if not self.logos_dir.exists():
                makedirs(self.logos_dir, exist_ok=True)
            files = logos(self.luzbuild, files)

        # return files
        return files

    def linker(self, compile_type: str = "dylib"):
        """Use a linker on the compiled files.

        :param str type: The type of files to link.
        """
        if compile_type == "dylib":
            out_name = resolve_path(f"{self.dir}/dylib/{self.name}/{self.name}.dylib")
        else:
            out_name = resolve_path(f"{self.dir}/bin/{self.name}/{self.name}")

        # check if linked files exist
        if len(self.files) == 0 and out_name.exists():
            return

        # build args
        build_flags = [
            "-fobjc-arc" if self.arc else "",
            f"-isysroot {self.luzbuild.sdk}",
            self.warnings,
            f"-O{self.optimization}",
            self.include,
            self.library_dirs,
            self.framework_dirs,
            self.libraries,
            self.frameworks,
            self.private_frameworks,
            f"-m{self.luzbuild.platform}-version-min={self.luzbuild.min_vers}",
            self.c_flags,
        ]
        # add dynamic lib to args
        if compile_type == "dylib":
            build_flags.append("-dynamiclib")
        # compile for each arch
        for arch in self.luzbuild.archs:
            try:
                self.luzbuild.c_compiler.compile(resolve_path(f"{self.dir}/obj/{self.name}/{arch}/*.o"), outfile=f"{self.dir}/obj/{self.name}/{arch}/{self.name}", args=build_flags + [f"-arch {arch}"])
            except:
                return f'An error occured when trying to link files for module "{self.name}" for architecture "{arch}".'

        # link
        try:
            check_output(f"{self.luzbuild.lipo} -create -output {out_name} {self.dir}/obj/{self.name}/*/{self.name}", shell=True)
        except:
            return f'An error occured when trying to lipo files for module "{self.name}".'

        try:
            # fix rpath
            rpath = "/var/jb/Library/Frameworks/" if self.luzbuild.rootless else "/Library/Frameworks"
            check_output(f"{self.luzbuild.install_name_tool} -add_rpath {rpath} {out_name}", shell=True)
        except:
            return f'An error occured when trying to add rpath to "{out_name}" for module "{self.name}".'

        if compile_type == "executable":
            try:
                check_output(f"{self.luzbuild.strip} {out_name}", shell=True)
            except:
                return f'An error occured when trying to strip "{out_name}" for module "{self.name}".'

        try:
            # run ldid
            check_output(f"{self.luzbuild.ldid} {self.entflag}{self.entfile} {out_name}", shell=True)
        except:
            return f'An error occured when trying codesign "{out_name}" for module "{self.name}".'

        self.remove_log_stdout(f'Linking compiled files to {compile_type} "{out_name.name}"...')

    def log(self, msg):
        log(msg, self.luzbuild.lock)

    def error(self, msg):
        error(msg, self.luzbuild.lock)

    def log_stdout(self, msg):
        log_stdout(msg, self.luzbuild.lock)

    def remove_log_stdout(self, msg):
        remove_log_stdout(msg, self.luzbuild.lock)
