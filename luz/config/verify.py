"""Verify the luzconf config."""

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
    def __init__(self, file_path: str = "luzconf.py", args: Namespace = None):
        """Verify the Luz.py config.

        :param str file_path: The path to the file to verify.
        :param Namespace args: The arguments passed to the program.
        """
        warnings = 0
        errors = 0
        try:
            super().__init__(file_path, args)
        except Exception as err:
            error(f"Failed to parse '{file_path}'.")
            error(f"Error: {err}")
            errors += 1

        if self.scripts != []:
            for script in self.scripts:
                if not script.type in ["preinst", "postinst", "prerm", "postrm"]:
                    warnings += 1
                    warn(f"Script type '{script.type}' is unknown. Valid scripts are 'preinst', 'postinst', 'prerm', and 'postrm'.")

        if "raw" in self.__dict__:
            # default meta
            default_meta = get_default_args(Meta.__init__)

            # default module
            default_module = get_default_args(Module.__init__)

            # default submodule
            default_submodule = get_default_args(Submodule.__init__)

            # contents
            with open(file_path, "r") as file:
                file_contents = file.read()

                # verify meta
                if not "Meta(" in file_contents:
                    warnings += 1
                    log("Meta() not found in file. Add it to the file to speed up build time.")
                else:
                    for attr in default_meta:
                        if getattr(self.meta, attr) == default_meta[attr]:
                            if f"{attr}={getattr(self.meta, attr)}" in file_contents:
                                warnings += 1
                                warn(f"Meta attribute '{attr}' is set to default value. You can remove it from the file.")

        log(f"Verification complete. {warnings} warning{'s' if warnings != 1 else ''} and {errors} error{'s' if errors != 1 else ''}.")
