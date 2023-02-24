# module imports
from multiprocessing.pool import ThreadPool
from os import makedirs
from shutil import copytree
from subprocess import check_output

# local imports
from ..module import ModuleBuilder
from ...common.logger import log, warn
from ...common.utils import resolve_path

class Tool(ModuleBuilder):
    def __init__(self, **kwargs):
        """Build a tool module."""
        # kwargs parsing
        super().__init__(kwargs.get("module"), kwargs.get("luz"))

        # files
        self.files = self.hash_files(self.module.files, "executable")

    def __compile_tool_file(self, file) -> bool:
        """Compile a tool file.

        :param str file: The file to compile.
        """
        # log
        log(f"({self.module.name}) Compiling '{str(file).replace(str(self.luz.path.absolute()), '')}'...")
        files_minus_to_compile = list(
            filter(lambda x: x != file and str(x).endswith(".swift"), self.files))
        # compile file
        try:
            pool = ThreadPool()
            if str(file).endswith(".swift"):
                pool.map(lambda x: self.compile_swift_arch(
                    file, files_minus_to_compile, x), self.meta.archs)
            else:
                pool.map(lambda x: self.compile_c_arch(file, x), self.meta.archs)

        except Exception as e:
            print(e)
            return f'An error occured when attempting to compile for module "{self.module.name}".'

    def __stage(self):
        """Stage a deb to be packaged."""
        # log
        log(f"({self.module.name}) Staging...")
        # dirs to make
        if self.module.install_dir is None:
            dirtomake = resolve_path(
                f"{self.luz.build_dir}/_/usr") if not self.meta.rootless else resolve_path(f"{self.luz.build_dir}/_/var/jb/usr")
            dirtocopy = resolve_path(
                f"{self.luz.build_dir}/_/usr/bin") if not self.meta.rootless else resolve_path(f"{self.luz.build_dir}/_/var/jb/usr/bin")
        else:
            if self.meta.rootless:
                warn(
                    f'({self.module.name}) Custom install directory was specified, and rootless is enabled. Prefixing path with /var/jb.')
            self.install_dir = resolve_path(self.module.install_dir)
            dirtomake = resolve_path(f"{self.luz.build_dir}/_/{self.module.install_dir.parent}") if not self.meta.rootless else resolve_path(
                f"{self.luz.build_dir}/_/var/jb/{self.module.install_dir.parent}")
            dirtocopy = resolve_path(f"{self.luz.build_dir}/_/{self.module.install_dir}") if not self.meta.rootless else resolve_path(
                f"{self.luz.build_dir}/_/var/jb/{self.module.install_dir}")
        # make proper dirs
        if not dirtomake.exists():
            makedirs(dirtomake, exist_ok=True)
        copytree(self.bin_dir, dirtocopy, dirs_exist_ok=True)

    def compile(self):
        """Compile module."""
        for arch in self.meta.archs:
            for x in self.files:
                check_output(f"rm -rf {self.obj_dir}/{arch}/{x.name}-*", shell=True)
            makedirs(f"{self.obj_dir}/{arch}", exist_ok=True)
        # compile files
        compile_results = self.luz.pool.map(
            self.__compile_tool_file, self.files)
        for result in compile_results:
            if result is not None:
                return result
        # link files
        linker_results = self.linker("executable")
        if linker_results is not None:
            return linker_results
        # stage deb
        if self.meta.pack:
            self.__stage()
    