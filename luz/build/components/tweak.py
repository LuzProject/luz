# module imports
from multiprocessing.pool import ThreadPool
from os import makedirs
from shutil import copytree
from subprocess import check_output

# local imports
from ..module import ModuleBuilder
from ...common.logger import log, warn
from ...common.utils import resolve_path

class Tweak(ModuleBuilder):
    def __init__(self, **kwargs):
        """Build a tool module."""
        # kwargs parsing
        super().__init__(kwargs.get("module"), kwargs.get("luz"))

        # files
        self.files = self.hash_files(self.module.files, "dylib", True)

    def __compile_tweak_file(self, file) -> bool:
        """Compile a tweak file.

        :param str file: The file to compile.
        """
        # log
        if file.get("old_path") is not None:
            file_formatted = str(file.get("old_path")).replace(
                str(self.luz.path.absolute()), '')
            if file_formatted != str(file.get("old_path")):
                file_formatted = "/".join(file_formatted.split("/")[1:])
            msg = f"({self.module.name}) Compiling '{file_formatted}'..."
        else:
            file_formatted = str(file.get("path")).replace(
                str(self.luz.path.absolute()), '')
            if file_formatted != str(file.get("path")):
                file_formatted = "/".join(file_formatted.split("/")[1:])
            msg = f"({self.module.name}) Compiling '{file_formatted}'..."

        log(msg, self.luz.lock)

        file = list(
            filter(
                lambda x: x == file.get("new_path") or x == file.get("path"),
                self.files_paths,
            )
        )[0]
        
        # compile file
        try:
            pool = ThreadPool()
            if str(file).endswith(".swift"):
                files_minus_to_compile = list(
                    filter(lambda x: x != file and str(x).endswith(".swift"), self.files_paths))
                pool.map(lambda x: self.compile_swift_arch(file, files_minus_to_compile, x), self.meta.archs)
            else:
                pool.map(lambda x: self.compile_c_arch(file, x), self.meta.archs)

        except:
            return f'An error occured when attempting to compile for module "{self.module.name}".'

    def __stage(self):
        """Stage a deb to be packaged."""
        # log
        log(f"({self.module.name}) Staging...", self.luz.lock)
        # dirs to make
        if self.module.install_dir is None:
            dirtomake = resolve_path(
                f"{self.luz.build_dir}/_/usr") if not self.meta.rootless else resolve_path(f"{self.luz.build_dir}/_/var/jb/usr")
            dirtocopy = resolve_path(
                f"{self.luz.build_dir}/_/usr/bin") if not self.meta.rootless else resolve_path(f"{self.luz.build_dir}/_/var/jb/usr/bin")
        else:
            if self.meta.rootless:
                warn(
                    f'({self.module.name}) Custom install directory was specified, and rootless is enabled. Prefixing path with /var/jb.', self.luz.lock)
            self.install_dir = resolve_path(self.module.install_dir)
            dirtomake = resolve_path(f"{self.luz.build_dir}/_/{self.module.install_dir.parent}") if not self.meta.rootless else resolve_path(
                f"{self.luz.build_dir}/_/var/jb/{self.module.install_dir.parent}")
            dirtocopy = resolve_path(f"{self.luz.build_dir}/_/{self.module.install_dir}") if not self.meta.rootless else resolve_path(
                f"{self.luz.build_dir}/_/var/jb/{self.module.install_dir}")
        # make proper dirs
        if not dirtomake.exists():
            makedirs(dirtomake, exist_ok=True)
        copytree(self.dylib_dir, dirtocopy, dirs_exist_ok=True)

        # plist
        with open(f"{dirtocopy}/{''.join(self.module.install_name.split('.')[:-1])}.plist", "w") as f:
            filtermsg = "Filter = {\n"
            # bundle filters
            if self.module.filter.get("bundles") is not None:
                filtermsg += "    Bundles = ( "
                for filter in self.module.filter.get("bundles"):
                    filtermsg += f'"{filter}", '
                filtermsg = filtermsg[:-2] + " );\n"
            # executables filters
            if self.module.filter.get("executables") is not None:
                filtermsg += "    Executables = ( "
                for executable in self.module.filter.get("executables"):
                    filtermsg += f'"{executable}", '
                filtermsg = filtermsg[:-2] + " );\n"
            filtermsg += "};"
            f.write(filtermsg)

    def compile(self):
        """Compile module."""
        # handle logos files
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

        for arch in self.meta.archs:
            for x in self.files_paths:
                check_output(f"rm -rf {self.obj_dir}/{arch}/{x.name}-*", shell=True)
            makedirs(f"{self.obj_dir}/{arch}", exist_ok=True)

        # compile files
        compile_results = self.luz.pool.map(
            self.__compile_tweak_file, self.files)
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
