# module imports
from concurrent.futures import ThreadPoolExecutor, wait
from os import makedirs
from shutil import rmtree
from subprocess import getoutput

# local imports
from ..common.deps import clone_headers, clone_libraries, logos
from ..common.logger import log
from ..common.utils import get_hash, resolve_path


class ModuleBuilder:
    """Module builder class."""

    def __init__(self, module, luz):
        """Initialize module builder.

        Args:
            module (Module): The module to build.
            luz (Luz): The luz object.
        """
        # variables
        self.module = module
        self.luz = luz
        self.meta = luz.meta
        self.control = luz.control

        # add necessary include files
        self.module.include_dirs.append(str(clone_headers(self.meta)))
        self.module.library_dirs.append(str(clone_libraries(self.meta)))

        # add custom files
        self.module.include_dirs.append(f"{self.meta.storage}/headers")
        self.module.library_dirs.append(f"{self.meta.storage}/lib")

        # swift
        for file in self.module.files:
            if str(file).endswith(".swift"):
                self.module.library_dirs.append("/usr/lib/swift")
                self.module.library_dirs.append(f"{self.meta.sdk}/usr/lib/swift")
                break

        # private frameworks
        if self.module.private_frameworks != []:
            if resolve_path(f"{self.meta.sdk}/System/Library/PrivateFrameworks").exists():
                self.module.framework_dirs.append(f"{self.meta.sdk}/System/Library/PrivateFrameworks")
            else:
                raise Exception(f"Private frameworks are not available on the SDK being used. ({self.meta.sdk})")

        # directories
        self.logos_dir = resolve_path(f"{self.luz.build_dir}/logos-processed")
        self.obj_dir = resolve_path(f"{self.luz.build_dir}/obj/{self.module.name}")
        self.dylib_dir = resolve_path(f"{self.luz.build_dir}/dylib/{self.module.name}")
        self.bin_dir = resolve_path(f"{self.luz.build_dir}/bin/{self.module.name}")

    def hash_files(self, files, compile_type: str = "dylib"):
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
        arch_count = len(self.meta.archs)
        # file path formatting
        for file in files:
            if not str(file).startswith("/"):
                file = f"{self.luz.path}/{file}"
            file_path = resolve_path(file)
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
            if "hashlist" not in self.luz.build_info:
                self.luz.build_info["hashlist"] = {}
            fhash = self.luz.build_info["hashlist"].get(str(file))
            new_hash = get_hash(file)
            if fhash is None:
                changed.append(file)
            elif fhash == new_hash:
                # variables
                object_paths = resolve_path(f"{self.obj_dir}/*/{file.name}*-*.o")
                lipod_paths = resolve_path(f"{self.obj_dir}/*/{self.module.install_name}")
                if len(object_paths) < arch_count or len(lipod_paths) < arch_count:
                    changed.append(file)
            elif fhash != new_hash:
                changed.append(file)
            # add to new hashes
            new_hashes[str(file)] = new_hash

        # hashes
        self.luz.update_hashlist(new_hashes)

        # files list
        files = changed if self.module.only_compile_changed else files_to_compile

        # handle files not needing compilation
        if len(files) == 0:
            log(
                f'Nothing to compile for module "{self.module.name}".',
                "🔨",
                self.module.abbreviated_name,
                self.luz.lock,
            )
            return []

        files = files_to_compile

        # use logos on files
        if not self.logos_dir.exists() and list(filter(lambda x: ".x" in x, [str(f) for f in files])) != []:
            makedirs(self.logos_dir, exist_ok=True)
        files = logos(self.meta, self.module, files)

        # pool
        self.pool = ThreadPoolExecutor(max_workers=(len(files) * arch_count))

        # return files
        return files

    def linker(self, compile_type: str = "dylib"):
        """Use a linker on the compiled files.

        :param str type: The type of files to link.
        """
        if compile_type == "dylib":
            out_name = resolve_path(f"{self.dylib_dir}/{self.module.install_name}")
        else:
            out_name = resolve_path(f"{self.bin_dir}/{self.module.install_name}")

        # check if linked files exist
        if len(self.files) == 0 and out_name.exists():
            return

        # log
        log(
            f'Linking compiled objects to "{self.module.install_name}"...',
            "🔗",
            self.module.abbreviated_name,
            self.luz.lock,
        )

        # build args
        build_flags = [
            "-fobjc-arc" if self.module.use_arc else "",
            f"-isysroot {self.meta.sdk}",
            f"-O{self.module.optimization}",
            ("-I" + " -I".join(self.module.include_dirs)) if self.module.include_dirs != [] else "",
            ("-L" + " -L".join(self.module.library_dirs)) if self.module.library_dirs != [] else "",
            ("-F" + " -F".join(self.module.framework_dirs)) if self.module.framework_dirs != [] else "",
            ("-l" + " -l".join(self.module.libraries)) if self.module.libraries != [] else "",
            ("-framework " + " -framework ".join(self.module.frameworks)) if self.module.frameworks != [] else "",
            ("-framework " + " -framework ".join(self.module.private_frameworks)) if self.module.private_frameworks != [] else "",
            f"-m{self.meta.platform}-version-min={self.meta.min_vers}",
            "-g" if self.meta.debug else "",
            f"-Wl,-install_name,{self.module.install_name},-rpath,{'/var/jb' if self.meta.rootless else ''}/usr/lib/,-rpath,{'/var/jb' if self.meta.rootless else ''}/Library/Frameworks/",
        ]
        build_flags.extend(self.module.warnings)
        build_flags.extend(self.module.linker_flags)
        # add dynamic lib to args
        if compile_type == "dylib":
            build_flags.append("-dynamiclib")
        # compile for each arch
        for arch in self.meta.archs:
            try:
                self.luz.c_compiler.compile(
                    resolve_path(f"{self.obj_dir}/{arch}/*.o"),
                    outfile=f"{self.obj_dir}/{arch}/{self.module.install_name}",
                    args=build_flags + [f"-arch {arch}"],
                )
            except:
                return f'An error occured when trying to link files for module "{self.module.name}" for architecture "{arch}".'

        # link
        try:
            compiled = [f"{self.obj_dir}/{arch}/{self.module.install_name}" for arch in self.meta.archs]
            getoutput(f"{self.meta.lipo} -create -output {out_name} {' '.join(compiled)}")
        except:
            return f'An error occured when trying to lipo files for module "{self.module.name}".'

        if compile_type == "executable" and self.meta.release:
            try:
                getoutput(f"{self.meta.strip} {out_name}")
            except:
                return f'An error occured when trying to strip "{out_name}" for module "{self.module.name}".'

        try:
            # run ldid
            getoutput(f"{self.meta.ldid} {' '.join(self.module.codesign_flags)} {out_name}")
        except:
            return f'An error occured when trying codesign "{out_name}" for module "{self.module.name}".'

    def handle_logos(self):
        """Handle files that have had Logos ran on them."""
        self.files_paths = []
        for file in self.files:
            new_path = ""
            # handle logos files
            if file.get("logos") == True:
                # new path
                new_path = file.get("new_path")
                # set original path
                orig_path = file.get("old_path")
                # include path
                include_path = "/".join(str(orig_path).split("/")[:-1])
                # add it to include if it's not already there
                if include_path not in self.module.include_dirs:
                    self.module.include_dirs.append(include_path)
            # handle normal files
            else:
                new_path = file.get("path")

            # add to files paths
            self.files_paths.append(new_path)

    def compile_file(self, file):
        # log
        if file.get("old_path") is not None:
            file_formatted = str(file.get("old_path")).replace(str(self.luz.path.absolute()), "")
            if file_formatted != str(file.get("old_path")):
                file_formatted = "/".join(file_formatted.split("/")[1:])
            msg = f'Compiling "{file_formatted}"...'
        else:
            file_formatted = str(file.get("path")).replace(str(self.luz.path.absolute()), "")
            if file_formatted != str(file.get("path")):
                file_formatted = "/".join(file_formatted.split("/")[1:])
            msg = f'Compiling "{file_formatted}"...'

        log(msg, "🔨", self.module.abbreviated_name, self.luz.lock)

        file = list(
            filter(
                lambda x: x == file.get("new_path") or x == file.get("path"),
                self.files_paths,
            )
        )[0]

        # compile file
        try:
            if str(file).endswith(".swift"):
                files_minus_to_compile = list(
                    filter(
                        lambda x: x != file and str(x).endswith(".swift"),
                        self.files_paths,
                    )
                )
                futures = [self.pool.submit(self.compile_swift_arch, file, files_minus_to_compile, x) for x in self.meta.archs]
            else:
                futures = [self.pool.submit(self.compile_c_arch, file, x) for x in self.meta.archs]
            self.wait(futures)

            # check results
            for future in futures:
                if future.result() is not None:
                    return f'An error occured when attempting to compile for module "{self.module.name}".'

        except:
            return f'An error occured when attempting to compile for module "{self.module.name}".'

    def compile_swift_arch(self, file, fmtc: list, arch: str):
        # format platform
        platform = "ios" if self.meta.platform == "iphoneos" else self.meta.platform
        # arch
        arch_formatted = f"-target {arch}-apple-{platform}{self.meta.min_vers}"
        # outname
        out_name = f"{self.obj_dir}/{arch}/{file.name}-{self.luz.now}"
        # define build flags
        build_flags = [
            "-frontend",
            "-c",
            f"-module-name {self.module.name}",
            f'-sdk "{self.meta.sdk}"',
            ("-I" + " -I".join(self.module.include_dirs)) if self.module.include_dirs != [] else "",
            ("-import-objc-header" + " -import-objc-header".join(self.module.bridging_headers)) if self.module.bridging_headers != [] else "",
            arch_formatted,
            f"-emit-module-path {out_name}.swiftmodule",
            "-g" if self.meta.debug else "",
            "-primary-file",
        ]
        build_flags.extend(self.module.swift_flags)
        rmtree(
            f"{self.obj_dir}/{arch}/{file.name}-*",
            ignore_errors=True,
        )
        # compile with swift using build flags
        try:
            self.luz.swift_compiler.compile([file] + fmtc, outfile=out_name + ".o", args=build_flags)
        except:
            return f'An error occured when trying to compile "{file}" for module "{self.module.name}".'

    def compile_c_arch(self, file, arch: str):
        # outname
        out_name = f"{self.obj_dir}/{arch}/{file.name}-{self.luz.now}.o"
        build_flags = [
            "-fobjc-arc" if self.module.use_arc else "",
            f"-isysroot {self.meta.sdk}",
            f"-O{self.module.optimization}",
            f"-arch {arch}",
            ("-I" + " -I".join(self.module.include_dirs)) if self.module.include_dirs != [] else "",
            f"-m{self.meta.platform}-version-min={self.meta.min_vers}",
            "-g" if self.meta.debug else "",
            f'-DLUZ_PACKAGE_VERSION=\\"{self.control.version}\\"' if self.control and self.control.raw != "" else "",
            "-c",
        ]
        build_flags.extend(self.module.c_flags)
        build_flags.extend(self.module.warnings)
        rmtree(
            f"{self.obj_dir}/{arch}/{file.name}-*",
            ignore_errors=True,
        )
        # compile with clang using build flags
        try:
            self.luz.c_compiler.compile(file, out_name, build_flags)
        except:
            return f'An error occured when attempting to compile "{file}" for module "{self.module.name}".'

    def wait(self, thread):
        wait(thread)
