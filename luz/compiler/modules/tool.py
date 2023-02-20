# module imports
from os import makedirs
from shutil import copytree, rmtree
from time import time

# local imports
from ...common.logger import warn
from .module import Module
from ...common.utils import resolve_path


class Tool(Module):
    def __init__(self, **kwargs):
        """Tool module class.

        :param dict module: Module dictionary to build
        :param str key: Module key name
        :param LuzBuild luzbuild: Luzbuild class
        """
        # time
        self.now = time()
        # kwargs parsing
        module = kwargs.get("module")
        super().__init__(module, kwargs.get("key"), kwargs.get("luzbuild"))

    def __compile_tool_file(self, file) -> bool:
        """Compile a tool file.

        :param str file: The file to compile.
        """
        files_minus_to_compile = list(
            filter(lambda x: x != file and str(x).endswith(".swift"), self.files)
        )
        # compile file
        try:
            if str(file).endswith(".swift"):
                # define build flags
                build_flags = [
                    "-frontend",
                    "-c",
                    f"-module-name {self.name}",
                    f'-sdk "{self.luzbuild.sdk}"',
                    self.include,
                    self.library_dirs,
                    self.framework_dirs,
                    self.libraries,
                    self.frameworks,
                    self.private_frameworks,
                    self.swift_flags,
                    '-g' if self.luzbuild.debug else '',
                    self.bridging_headers,
                ]
                # format platform
                platform = (
                    "ios"
                    if self.luzbuild.platform == "iphoneos"
                    else self.luzbuild.platform
                )
                for arch in self.luzbuild.archs:
                    rmtree(
                        f"{self.dir}/obj/{self.name}/{arch}/{file.name}-*",
                        ignore_errors=True,
                    )
                    out_name = (
                        f"{self.dir}/obj/{self.name}/{arch}/{file.name}-{self.now}"
                    )
                    # arch
                    arch_formatted = (
                        f"-target {arch}-apple-{platform}{self.luzbuild.min_vers}"
                    )
                    # compile with swift using build flags
                    self.luzbuild.swift_compiler.compile(
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
                for arch in self.luzbuild.archs:
                    rmtree(
                        f"{self.dir}/obj/{self.name}/{arch}/{file.name}-*",
                        ignore_errors=True,
                    )
                    out_name = (
                        f"{self.dir}/obj/{self.name}/{arch}/{file.name}-{self.now}.o"
                    )
                    build_flags = [
                        "-fobjc-arc" if self.arc else "",
                        f"-isysroot {self.luzbuild.sdk}",
                        self.warnings,
                        f"-O{self.optimization}",
                        f"-arch {arch}",
                        self.include,
                        f"-m{self.luzbuild.platform}-version-min={self.luzbuild.min_vers}",
                        self.c_flags,
                        '-g' if self.luzbuild.debug else '',
                        "-c",
                    ]
                    # compile with clang using build flags
                    self.luzbuild.c_compiler.compile(file, out_name, build_flags)

        except:
            return (
                f'An error occured when attempting to compile for module "{self.name}".'
            )

    def __stage(self):
        """Stage a deb to be packaged."""
        # dirs to make
        if self.install_dir is None:
            dirtomake = (
                resolve_path(f"{self.dir}/_/usr")
                if not self.luzbuild.rootless
                else resolve_path(f"{self.dir}/_/var/jb/usr")
            )
            dirtocopy = (
                resolve_path(f"{self.dir}/_/usr/bin")
                if not self.luzbuild.rootless
                else resolve_path(f"{self.dir}/_/var/jb/usr/bin")
            )
        else:
            if self.luzbuild.rootless:
                warn(
                    f'Custom install directory for module "{self.name}" was specified, and rootless is enabled. Prefixing path with /var/jb.'
                )
            self.install_dir = resolve_path(self.install_dir)
            dirtomake = (
                resolve_path(f"{self.dir}/_/{self.install_dir.parent}")
                if not self.luzbuild.rootless
                else resolve_path(f"{self.dir}/_/var/jb/{self.install_dir.parent}")
            )
            dirtocopy = (
                resolve_path(f"{self.dir}/_/{self.install_dir}")
                if not self.luzbuild.rootless
                else resolve_path(f"{self.dir}/_/var/jb/{self.install_dir}")
            )
        # make proper dirs
        if not dirtomake.exists():
            makedirs(dirtomake, exist_ok=True)
        copytree(self.bin_dir, dirtocopy, dirs_exist_ok=True)

    def compile(self):
        """Compile the specified self."""
        for arch in self.luzbuild.archs:
            rmtree(f"{self.dir}/obj/{self.name}/{arch}", ignore_errors=True)
            makedirs(f"{self.dir}/obj/{self.name}/{arch}", exist_ok=True)
        # compile files
        compile_results = self.luzbuild.pool.map(self.__compile_tool_file, self.files)
        for result in compile_results:
            if result is not None:
                return result
        # link files
        linker_results = self.linker("executable")
        if linker_results is not None:
            return linker_results
        # stage deb
        if self.luzbuild.should_pack:
            self.__stage()
