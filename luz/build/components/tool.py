# module imports
from os import makedirs
from shutil import copytree

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

    def stage(self):
        """Stage a deb to be packaged."""
        # log
        log(f"Staging...", "📦", self.module.abbreviated_name, self.luz.lock)
        # before stage
        if self.module.before_stage:
            self.module.before_stage()
        # dirs to make
        if self.module.install_dir is None:
            dirtomake = resolve_path(f"{self.luz.build_dir}/_/usr") if not self.meta.rootless else resolve_path(f"{self.luz.build_dir}/_/var/jb/usr")
            dirtocopy = resolve_path(f"{self.luz.build_dir}/_/usr/bin") if not self.meta.rootless else resolve_path(f"{self.luz.build_dir}/_/var/jb/usr/bin")
        else:
            if self.meta.rootless:
                warn("Rootless is enabled, but a custom install_dir is set. Proceed with caution.", lock=self.luz.lock)
            self.install_dir = resolve_path(self.module.install_dir)
            dirtomake = resolve_path(f"{self.luz.build_dir}/_/{self.module.install_dir.parent}")
            dirtocopy = resolve_path(f"{self.luz.build_dir}/_/{self.module.install_dir}")
        # make proper dirs
        if not dirtomake.exists():
            makedirs(dirtomake, exist_ok=True)
        copytree(self.bin_dir, dirtocopy, dirs_exist_ok=True)
        # after stage
        if self.module.after_stage:
            self.module.after_stage()
            