# module imports
from os import makedirs
from shutil import copyfile, copytree

# local imports
from ..module import ModuleBuilder
from ...common.logger import log
from ...common.utils import resolve_path


class Framework(ModuleBuilder):
    def __init__(self, **kwargs):
        """Build a tool module."""
        # kwargs parsing
        super().__init__(kwargs.get("module"), kwargs.get("luz"))

    def stage(self):
        """Stage a deb to be packaged."""
        # log
        log(f"Staging...", "📦", self.module.abbreviated_name, self.luz.lock)
        # before stage
        if self.module.before_stage:
            self.module.before_stage()
        # dirs to make
        dirtocopy = self.meta.root_dir / self.module.install_dir
        # make proper dirs
        if not dirtocopy.parent.exists():
            makedirs(dirtocopy.parent, exist_ok=True)
        copytree(self.dylib_dir, dirtocopy, dirs_exist_ok=True)
        # copy resources
        resources_path = resolve_path(self.module.resources_dir)
        if not resources_path.exists():
            return f'Resources/ folder for "{self.module.name}" does not exist. (path: {resources_path}))'
        # copy resources
        copytree(resources_path, dirtocopy, dirs_exist_ok=True)
        # copy headers
        for header in self.module.public_headers:
            header_path = resolve_path(header)
            if not header_path.exists():
                return f'Provided public header for "{self.module.name}" does not exist. (path: {header_path}))'
            # copy header
            copyfile(header_path, dirtocopy / header_path.name)
        # after stage
        if self.module.after_stage:
            self.module.after_stage()
