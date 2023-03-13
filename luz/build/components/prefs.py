# module imports
from os import makedirs
from shutil import copytree

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

    def stage(self):
        """Stage a deb to be packaged."""
        # log
        log(f"Staging...", "📦", self.module.abbreviated_name, self.luz.lock)
        # before stage
        if self.module.before_stage:
            self.module.before_stage()
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
        if self.module.after_stage:
            self.module.after_stage()
