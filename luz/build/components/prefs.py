# module imports
from multiprocessing.pool import ThreadPool
from os import makedirs
from shutil import copytree
from subprocess import check_output

# local imports
from ..module import ModuleBuilder
from ...common.logger import log
from ...common.utils import resolve_path

class Preferences(ModuleBuilder):
    def __init__(self, **kwargs):
        """Build a tool module."""
        # kwargs parsing
        super().__init__(kwargs.get("module"), kwargs.get("luz"))

        # files
        self.files = self.hash_files(self.module.files, "dylib")

    def __stage(self):
        """Stage a deb to be packaged."""
        # log
        log(f"Staging...", "📦", self.module.abbreviated_name, self.luz.lock)
        # before stage
        if self.module.before_stage: self.module.before_stage()
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
        # after stage
        if self.module.after_stage: self.module.after_stage()

    def compile(self):
        """Compile module."""
        # handle logos
        self.handle_logos()
        # clean arch dirs
        for arch in self.meta.archs:
            for x in self.files_paths:
                check_output(f"rm -rf {self.obj_dir}/{arch}/{x.name}-*", shell=True)
            makedirs(f"{self.obj_dir}/{arch}", exist_ok=True)
        # compile files
        futures = [self.luz.pool.submit(self.compile_file, file) for file in self.files]
        self.wait(futures)
        for result in futures:
            if result.result() is not None:
                return result
        # link files
        linker_results = self.linker("dylib")
        if linker_results is not None:
            return linker_results
        # stage deb
        if self.meta.pack:
            self.__stage()
