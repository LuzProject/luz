# module imports
from os import makedirs
from shutil import copytree

# local imports
from ..module import ModuleBuilder
from ...common.logger import log


class Tweak(ModuleBuilder):
    def __init__(self, **kwargs):
        """Build a tool module."""
        # kwargs parsing
        super().__init__(kwargs.get("module"), kwargs.get("luz"))

    def stage(self):
        """Stage a deb to be packaged."""
        # log
        log(f"Staging...", "📦", self.module.abbreviated_name, self.luz.lock)
        # before stage
        if self.module.before_stage is not None:
            self.module.before_stage()
        # dirs to make
        dirtocopy = self.meta.root_dir / self.module.install_dir
        # make proper dirs
        if not dirtocopy.parent.exists():
            makedirs(dirtocopy.parent, exist_ok=True)
        copytree(self.dylib_dir, dirtocopy, dirs_exist_ok=True)

        # plist
        with open(f"{dirtocopy}/{''.join(self.module.install_name.split('.')[:-1])}.plist", "w") as file:
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
            file.write(filtermsg)
        # after stage
        if self.module.after_stage is not None:
            self.module.after_stage()
