# module imports
from argparse import Namespace
from inspect import Parameter, signature

# local imports
from . import Luz, Meta, Module, Submodule
from ..common.logger import error, log, warn


def get_default_args(func):
    sig = signature(func)
    return {k: v.default for k, v in sig.parameters.items() if v.default is not Parameter.empty}


class Verify(Luz):
    def __init__(self, file_path: str = "luz.py", args: Namespace = None):
        warnings = 0
        errors = 0
        try:
            super().__init__(file_path, args)
        except Exception as e:
            error(f"Failed to parse '{file_path}'.")
            error(f"Error: {e}")
            errors += 1

        if "raw" in self.__dict__:
            # default meta
            default_meta = get_default_args(Meta.__init__)

            # default module
            default_module = get_default_args(Module.__init__)

            # default submodule
            default_submodule = get_default_args(Submodule.__init__)

            # contents
            file_contents = open(file_path, "r").read()

            # verify meta
            if not "Meta(" in file_contents:
                warnings += 1
                log("Meta() not found in file. Add it to the file to speed up build time.")
            else:
                for attr in default_meta:
                    if getattr(self.meta, attr) == default_meta[attr]:
                        if f"{attr}=" in file_contents:
                            warnings += 1
                            warn(f"Meta attribute '{attr}' is set to default value. You can remove it from the file.")

            # verify modules
            for module in self.modules:
                for attr in default_module:
                    if getattr(module, attr) == default_module[attr]:
                        if f"{attr}=" in file_contents:
                            warnings += 1
                            warn(f"{module.name} module attribute '{attr}' is set to default value. You can remove it from the file.")

            # verify submodules
            for sm in self.submodules:
                for attr in default_submodule:
                    try:
                        if getattr(sm, attr) == default_submodule[attr]:
                            if f"{attr}=" in file_contents:
                                warnings += 1
                                warn(f"{sm.name} submodule attribute '{attr}' is set to default value. You can remove it from the file.")
                    except AttributeError:
                        pass

        log(f"Verification complete. {warnings} warning{'s' if warnings != 1 else ''} and {errors} error{'s' if errors != 1 else ''}.")
