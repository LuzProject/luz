# module imports
from os import makedirs
from subprocess import getoutput
from time import time

# local imports
from ..common.deps import clone_headers, clone_libraries, logos
from ..common.logger import log
from ..common.utils import get_hash, resolve_path

class ModuleBuilder():
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
        self.module.include_dirs.append(f'{self.meta.storage}/headers')
        self.module.library_dirs.append(f'{self.meta.storage}/lib')

        # swift
        for file in self.module.files:
            if str(file).endswith(".swift"):
                self.module.library_dirs.append('/usr/lib/swift')
                self.module.library_dirs.append(f'{self.meta.sdk}/usr/lib/swift')
                break

        # fix rootless
        if self.meta.platform != "iphoneos": self.meta.rootless = False

        # directories
        self.logos_dir = resolve_path(f"{self.luz.build_dir}/logos-processed/{self.module.name}")
        self.obj_dir = resolve_path(f"{self.luz.build_dir}/obj/{self.module.name}")
        self.dylib_dir = resolve_path(f"{self.luz.build_dir}/dylib/{self.module.name}")
        self.bin_dir = resolve_path(f"{self.luz.build_dir}/bin/{self.module.name}")

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
            fhash = self.luz.hashlist.get(str(file))
            new_hash = get_hash(file)
            if fhash is None:
                changed.append(file)
            elif fhash == new_hash:
                # variables
                object_paths = resolve_path(
                    f"{self.obj_dir}/*/{file.name}*-*.o")
                lipod_paths = resolve_path(
                    f"{self.obj_dir}/*/{self.module.install_name}")
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
            log(f'Nothing to compile for module "{self.module.name}".')
            return []

        files = files_to_compile

        # use logos files if necessary
        if run_logos and filter(lambda x: ".x" in x, files) != []:
            if not self.logos_dir.exists():
                makedirs(self.logos_dir, exist_ok=True)
            files = logos(self.meta, files)

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
        if len(self.module.files) == 0 and out_name.exists():
            return

        # log
        log(f"({self.module.name}) Linking compiled objects to '{self.module.install_name}'...")

        # build args
        build_flags = [
            "-fobjc-arc" if self.module.use_arc else "",
            f"-isysroot {self.meta.sdk}",
            self.module.warnings,
            f"-O{self.module.optimization}",
            ("-I" + " -I".join(self.module.include_dirs)) if self.module.include_dirs != [] else "",
            ("-L" + " -L".join(self.module.library_dirs)) if self.module.library_dirs != [] else "",
            ("-F" + " -F".join(self.module.framework_dirs)) if self.module.framework_dirs != [] else "",
            ("-l" + " -l".join(self.module.libraries)) if self.module.libraries != [] else "",
            ("-framework " + " -framework ".join(self.module.frameworks)) if self.module.frameworks != [] else "",
            ("-framework " + " -framework ".join(self.module.private_frameworks)) if self.module.private_frameworks != [] else "",
            f"-m{self.meta.platform}-version-min={self.meta.min_vers}",
            f'-DLUZ_PACKAGE_VERSION="{self.control.version}"' if self.control and self.control.raw != "" else "",
            "-g" if self.meta.debug else "",
            self.module.c_flags,
        ]
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
            getoutput(
                f"{self.meta.lipo} -create -output {out_name} {' '.join(compiled)}"
            )
        except:
            return f'An error occured when trying to lipo files for module "{self.module.name}".'

        try:
            # fix rpath
            rpath = "/var/jb/Library/Frameworks/" if self.meta.rootless else "/Library/Frameworks"
            getoutput(
                f"{self.meta.install_name_tool} -add_rpath {rpath} {out_name}"
            )
        except:
            return f'An error occured when trying to add rpath to "{out_name}" for module "{self.module.name}".'

        if compile_type == "executable" and self.meta.release:
            try:
                getoutput(f"{self.meta.strip} {out_name}")
            except:
                return f'An error occured when trying to strip "{out_name}" for module "{self.module.name}".'

        try:
            # run ldid
            getoutput(
                f"{self.meta.ldid} {self.module.codesign_flags} {out_name}"
            )
        except:
            return f'An error occured when trying codesign "{out_name}" for module "{self.module.name}".'