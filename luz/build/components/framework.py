# Copyright (c) 2026 Jaidan Arenas
# module imports
from os import makedirs
from shutil import copy2, copyfile, copytree

# local imports
from ..module import ModuleBuilder
from ...common.logger import log
from ...common.utils import resolve_path


class Framework(ModuleBuilder):
    def __init__(self, **kwargs):
        """Build a framework module."""
        # kwargs parsing
        super().__init__(kwargs.get("module"), kwargs.get("luz"))

    def stage(self):
        """Stage a flat Apple framework bundle in the package tree.

        The compiled binary is placed at ``<Name>.framework/<Name>``. Public
        headers live in ``Headers/``. Files from ``resources_dir`` are copied
        to ``Resources/`` except ``Info.plist``, which Apple framework loaders
        expect at the framework bundle root.
        """
        # log
        log(f"Staging...", "📦", self.module.abbreviated_name, self.luz.lock)
        # before stage
        if self.module.before_stage:
            self.module.before_stage()
        framework_dir = self.meta.root_dir / self.module.install_dir
        framework_dir.mkdir(parents=True, exist_ok=True)

        # The linker output directory contains the framework executable. Keep
        # it at the bundle root rather than nesting it under Resources.
        copytree(self.dylib_dir, framework_dir, dirs_exist_ok=True)

        # Resources are opt-in, but a generated framework supplies Info.plist
        # here. It is placed at the bundle root; all other files retain a
        # predictable Resources/ namespace.
        resources_path = resolve_path(self.module.resources_dir)
        if not resources_path.exists():
            return f'Resources folder for "{self.module.name}" does not exist. (path: {resources_path})'
        resources_dir = framework_dir / "Resources"
        for resource in resources_path.iterdir():
            destination = framework_dir / "Info.plist" if resource.name == "Info.plist" else resources_dir / resource.name
            if resource.is_dir():
                copytree(resource, destination, dirs_exist_ok=True)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                copy2(resource, destination)

        # Public headers belong in Headers/, never beside the binary.
        headers_dir = framework_dir / "Headers"
        for header in self.module.public_headers:
            header_path = resolve_path(header)
            if not header_path.exists():
                return f'Provided public header for "{self.module.name}" does not exist. (path: {header_path})'
            headers_dir.mkdir(parents=True, exist_ok=True)
            copyfile(header_path, headers_dir / header_path.name)
        # after stage
        if self.module.after_stage:
            self.module.after_stage()
