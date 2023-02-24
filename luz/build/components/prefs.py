# module imports
from multiprocessing.pool import ThreadPool
from os import makedirs
from shutil import copytree
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
        file_formatted = str(file).replace(str(self.luz.path.absolute()), '')
        if file_formatted != str(file):
            file_formatted = "/".join(file_formatted.split("/")[1:])
        log(f"({self.module.name}) Compiling '{file_formatted}'...", self.luz.lock)
        
        # compile file
        try:
            pool = ThreadPool()
            if str(file).endswith(".swift"):
                files_minus_to_compile = list(
                    filter(lambda x: x != file and str(x).endswith(".swift"), self.files))
                # compile archs
                pool.map(lambda x: self.compile_swift_arch(
                    file, files_minus_to_compile, x), self.meta.archs)
            else:
                # compile archs
                pool.map(lambda x: self.compile_c_arch(file, x), self.meta.archs)
                    
        except:
            return f'An error occured when attempting to compile for module "{self.module.name}".'

    def __stage(self):
        """Stage a deb to be packaged."""
        # log
        log(f"({self.module.name}) Staging...", self.luz.lock)
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
