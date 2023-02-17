# module imports
from os import makedirs
from shutil import copytree, rmtree
from time import time

# local imports
from ...common.logger import warn
from .module import Module
from ...common.utils import resolve_path


class Tweak(Module):
    def __init__(self, **kwargs):
        """Tweak module class

        :param dict module: Module dictionary to build
        :param str key: Module key name
        :param LuzBuild luzbuild: Luzbuild class
        """
        # current time
        self.now = time()
        # kwargs parsing
        module = kwargs.get("module")
        super().__init__(module, kwargs.get("key"), kwargs.get("luzbuild"))

    def __compile_tweak_file(self, file):
        """Compile a tweak file.

        :param str file: The file to compile.
        """
        file = list(filter(lambda x: x == file.get("new_path") or x == file.get("path"), self.files_paths))[0]
        files_minus_to_compile = list(filter(lambda x: x != file and str(x).endswith(".swift"), self.files_paths))
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
                    self.bridging_headers,
                ]
                # format platform
                platform = "ios" if self.luzbuild.platform == "iphoneos" else self.luzbuild.platform
                for arch in self.luzbuild.archs:
                    rmtree(f"{self.dir}/obj/{self.name}/{arch}/{file.name}-*", ignore_errors=True)
                    out_name = f"{self.dir}/obj/{self.name}/{arch}/{file.name}-{self.now}"
                    # arch
                    arch_formatted = f"-target {arch}-apple-{platform}{self.luzbuild.min_vers}"
                    # compile with swift using build flags
                    self.luzbuild.swift_compiler.compile(
                        [file] + files_minus_to_compile, outfile=out_name + ".o", args=build_flags + [arch_formatted, f"-emit-module-path {out_name}.swiftmodule", "-primary-file"]
                    )
            else:
                for arch in self.luzbuild.archs:
                    rmtree(f"{self.dir}/obj/{self.name}/{arch}/{file.name}-*", ignore_errors=True)
                    out_name = f"{self.dir}/obj/{self.name}/{arch}/{file.name}-{self.now}.o"
                    build_flags = [
                        "-fobjc-arc" if self.arc else "",
                        f"-isysroot {self.luzbuild.sdk}",
                        self.warnings,
                        f"-O{self.optimization}",
                        f"-arch {arch}",
                        self.include,
                        f"-m{self.luzbuild.platform}-version-min={self.luzbuild.min_vers}",
                        self.c_flags,
                        "-c",
                    ]
                    # compile with clang using build flags
                    self.luzbuild.c_compiler.compile(file, out_name, build_flags)

        except:
            return f'An error occured when attempting to compile for module "{self.name}".'

    def __stage(self):
        """Stage a deb to be packaged."""
        # dirs to make
        if self.install_dir is None:
            dirtomake = resolve_path(f"{self.dir}/_/Library/MobileSubstrate/") if not self.luzbuild.rootless else resolve_path(f"{self.dir}/_/var/jb/usr/lib/")
            dirtocopy = resolve_path(f"{self.dir}/_/Library/MobileSubstrate/DynamicLibraries/") if not self.luzbuild.rootless else resolve_path(f"{self.dir}/_/var/jb/usr/lib/TweakInject")
        else:
            if self.luzbuild.rootless:
                warn(f'Custom install directory for module "{self.name}" was specified, and rootless is enabled. Prefixing path with /var/jb.')
            self.install_dir = resolve_path(self.install_dir)
            dirtomake = resolve_path(f"{self.dir}/_/{self.install_dir.parent}") if not self.luzbuild.rootless else resolve_path(f"{self.dir}/_/var/jb/{self.install_dir.parent}")
            dirtocopy = resolve_path(f"{self.dir}/_/{self.install_dir}") if not self.luzbuild.rootless else resolve_path(f"{self.dir}/_/var/jb/{self.install_dir}")
        # make proper dirs
        if not dirtomake.exists():
            makedirs(dirtomake, exist_ok=True)
        copytree(f"{self.dir}/dylib/{self.name}", dirtocopy, dirs_exist_ok=True)
        with open(f"{dirtocopy}/{self.name}.plist", "w") as f:
            filtermsg = "Filter = {\n"
            # bundle filters
            if self.filter.get("bundles") is not None:
                filtermsg += "    Bundles = ( "
                for filter in self.filter.get("bundles"):
                    filtermsg += f'"{filter}", '
                filtermsg = filtermsg[:-2] + " );\n"
            # executables filters
            if self.filter.get("executables") is not None:
                filtermsg += "    Executables = ( "
                for executable in self.filter.get("executables"):
                    filtermsg += f'"{executable}", '
                filtermsg = filtermsg[:-2] + " );\n"
            filtermsg += "};"
            f.write(filtermsg)

    def compile(self):
        """Compile."""
        for arch in self.luzbuild.archs:
            rmtree(f"{self.dir}/obj/{self.name}/{arch}", ignore_errors=True)
            makedirs(f"{self.dir}/obj/{self.name}/{arch}", exist_ok=True)
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
                if include_path not in self.include:
                    self.include += " -I" + include_path
            else:
                new_path = file.get("path")
            # handle normal files
            self.files_paths.append(new_path)
        # compile files
        compile_results = self.luzbuild.pool.map(self.__compile_tweak_file, self.files)
        for result in compile_results:
            if result is not None:
                return result

        # link files
        linker_results = self.linker()
        if linker_results is not None:
            return linker_results
        # stage deb
        if self.luzbuild.should_pack:
            self.__stage()
