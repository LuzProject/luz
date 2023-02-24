# module imports
from os import makedirs
from shutil import copytree, rmtree
from subprocess import check_output

# local imports
from ..module import ModuleBuilder
from ...common.logger import log, warn
from ...common.utils import resolve_path

class Preferences(ModuleBuilder):
    def __init__(self, **kwargs):
        """Build a tool module."""
        # kwargs parsing
        super().__init__(kwargs.get("module"), kwargs.get("luz"))

        # files
        self.files = self.hash_files(self.module.files, "dylib", True)

    def __compile_prefs_file(self, file) -> bool:
        """Compile a preferences file.

        :param str file: The file to compile.
        """
        # log
        log(f"({self.module.name}) Compiling '{str(file).replace(str(self.luz.path.absolute()), '')}'...")
        files_minus_to_compile = list(
            filter(lambda x: x != file and str(x).endswith(".swift"), self.files))
        
        # compile file
        try:
            if str(file).endswith(".swift"):
                # define build flags
                build_flags = [
                    "-frontend",
                    "-c",
                    f"-module-name {self.module.name}",
                    f'-sdk "{self.meta.sdk}"',
                    ("-I" + " -I".join(self.module.include_dirs)
                     ) if self.module.include_dirs != [] else "",
                    ("-L" + " -L".join(self.module.library_dirs)
                     ) if self.module.library_dirs != [] else "",
                    ("-F" + " -F".join(self.module.framework_dirs)
                     ) if self.module.framework_dirs != [] else "",
                    ("-l" + " -l".join(self.module.libraries)
                     ) if self.module.libraries != [] else "",
                    ("-framework " + " -framework ".join(self.module.frameworks)
                     ) if self.module.frameworks != [] else "",
                    ("-framework " + " -framework ".join(self.module.private_frameworks)
                     ) if self.module.private_frameworks != [] else "",
                    " ".join(
                        self.module.swift_flags) if self.module.swift_flags != [] else "",
                    "-g" if self.meta.debug else "",
                    " ".join(
                        self.module.bridging_headers) if self.module.bridging_headers != [] else "",
                ]
                # format platform
                platform = "ios" if self.meta.platform == "iphoneos" else self.meta.platform
                for arch in self.meta.archs:
                    rmtree(
                        f"{self.obj_dir}/{arch}/{file.name}-*",
                        ignore_errors=True,
                    )
                    out_name = f"{self.obj_dir}/{arch}/{file.name}-{self.luz.now}"
                    # arch
                    arch_formatted = f"-target {arch}-apple-{platform}{self.meta.min_vers}"
                    # compile with swift using build flags
                    self.luz.swift_compiler.compile(
                        [file] + files_minus_to_compile,
                        outfile=out_name + ".o",
                        args=build_flags
                        + [
                            arch_formatted,
                            f"-emit-module-path {out_name}.swiftmodule",
                            "-primary-file",
                        ],
                    )
            else:
                for arch in self.meta.archs:
                    rmtree(
                        f"{self.obj_dir}/{arch}/{file.name}-*",
                        ignore_errors=True,
                    )
                    out_name = f"{self.obj_dir}/{arch}/{file.name}-{self.luz.now}.o"
                    build_flags = [
                        "-fobjc-arc" if self.module.use_arc else "",
                        f"-isysroot {self.meta.sdk}",
                        self.module.warnings,
                        f"-O{self.module.optimization}",
                        f"-arch {arch}",
                        ("-I" + " -I".join(self.module.include_dirs)
                         ) if self.module.include_dirs != [] else "",
                        f"-m{self.meta.platform}-version-min={self.meta.min_vers}",
                        " ".join(
                            self.module.c_flags) if self.module.c_flags != [] else "",
                        "-g" if self.meta.debug else "",
                        "-c",
                    ]
                    # compile with clang using build flags
                    self.luz.c_compiler.compile(
                        file, out_name, build_flags)

        except:
            return f'An error occured when attempting to compile for module "{self.module.name}".'

    def __stage(self):
        """Stage a deb to be packaged."""
        # log
        log(f"({self.module.name}) Staging...")
        """Stage a deb to be packaged."""
        # dirs to make
        dirtomake = resolve_path(f"{self.luz.build_dir}/_/Library/PreferenceBundles/") if not self.meta.rootless else resolve_path(f"{self.luz.build_dir}/_/var/jb/Library/PreferenceBundles/")
        dirtocopy = (
            resolve_path(f"{self.luz.build_dir}/_/Library/PreferenceBundles/{self.module.name}.bundle")
            if not self.meta.rootless
            else resolve_path(f"{self.luz.build_dir}/_/var/jb/Library/PreferenceBundles/{self.module.name}.bundle")
        )
        # make proper dirs
        if not dirtomake.exists():
            makedirs(dirtomake, exist_ok=True)
        copytree(self.dylib_dir, dirtocopy, dirs_exist_ok=True)
        # copy resources
        resources_path = resolve_path(f"{self.luz.path}/Resources")
        if not resources_path.exists():
            return f'Resources/ folder for "{self.module.name}" does not exist'
        # copy resources
        copytree(resources_path, dirtocopy, dirs_exist_ok=True)

    def compile(self):
        """Compile module."""
        for arch in self.meta.archs:
            for x in self.files:
                check_output(
                    f"rm -rf {self.obj_dir}/{arch}/{x.name}-*", shell=True)
            makedirs(f"{self.obj_dir}/{arch}", exist_ok=True)

        # compile files
        compile_results = self.luz.pool.map(
            self.__compile_prefs_file, self.files)
        for result in compile_results:
            if result is not None:
                return result
        # link files
        linker_results = self.linker("dylib")
        if linker_results is not None:
            return linker_results
        # stage deb
        if self.meta.pack:
            self.__stage()
