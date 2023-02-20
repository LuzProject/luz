# module imports
from os import rename

# local imports
from ...common.logger import ask, error
from ...common.utils import resolve_path
from .module import Module


class Preferences(Module):
    def __init__(self):
        # type
        self.type = "preferences"
        # valid source types
        self.VALID = ["objc", "swift"]
        # srctype
        self.srctype = self.__ask_for("source type", "objc").lower()
        if self.srctype not in self.VALID:
            error(f'Invalid source type: {self.srctype}. Valid types: {", ".join(self.VALID)}')
            exit(1)

        # init super class
        super().__init__(self.type, self.srctype)

        # get keys
        self.name = self.__ask_for("name")
        self.id = self.__ask_for("bundle ID", f"com.yourcompany.{self.name.lower()}")
        # prefix
        self.prefix = self.__ask_for("unique bundle prefix", "XX") if self.srctype == "objc" else ""
        # add values to dict
        self.dict.update(
            {
                "modules": {
                    self.name: {
                        "type": "preferences",
                        "files": [f"Sources/{self.prefix}RootListController.m" if self.srctype != "swift" else f"Sources/RootListController.swift"],
                    }
                }
            }
        )
        # add swift bridging header
        if self.srctype == "swift":
            self.dict["modules"][self.name]["bridgingHeaders"] = [f"Sources/{self.name}-Bridging-Header.h"]
        # folder
        self.folder = resolve_path(
            self.__ask_for(
                "folder for project",
                self.control["name"] if self.control is not None else self.name,
            )
        )
        # write to yaml
        self.write_to_file(self.folder)

    def __ask_for(self, key: str, default: str = None, dsc: str = "What", dsc1: str = "is") -> str:
        """Ask for a value.

        :param str key: The key to ask for.
        :param str default: The default value.
        :param str dsc: The descriptor of the question.
        :param str dsc1: The descriptor of the question.
        :return: The value.
        """
        if default is not None:
            val = ask(f'{dsc} {dsc1} these {self.type}\'s {key}? (enter for "{default}")')
            if val == "":
                return default
        else:
            val = ask(f"{dsc} {dsc1} these {self.type}'s {key}?")
            if val == "":
                error("You must enter a value.")
                val = ask(f"{dsc} {dsc1} this {self.type}'s {key}?")
        return val

    def after_untar(self):
        """Do something after the untar."""
        # move source files
        if self.srctype == "objc":
            rename(
                f"{self.folder}/Sources/XXXRootListController.m",
                f"{self.folder}/Sources/{self.prefix}RootListController.m",
            )
            rename(
                f"{self.folder}/Sources/XXXRootListController.h",
                f"{self.folder}/Sources/{self.prefix}RootListController.h",
            )
            # fix files
            content = open(f"{self.folder}/Sources/{self.prefix}RootListController.m", "r").read()
            with open(f"{self.folder}/Sources/{self.prefix}RootListController.m", "w") as f:
                content = content.replace("REPLACEWITHPREFIX", self.prefix)
                f.write(content)
            content = open(f"{self.folder}/Sources/{self.prefix}RootListController.h", "r").read()
            with open(f"{self.folder}/Sources/{self.prefix}RootListController.h", "w") as f:
                content = content.replace("REPLACEWITHPREFIX", self.prefix)
                f.write(content)
        else:
            rename(
                f"{self.folder}/Sources/X-Bridging-Header.h",
                f"{self.folder}/Sources/{self.name}-Bridging-Header.h",
            )

        # move plist
        rename(
            f"{self.folder}/layout/Library/PreferenceLoader/Preferences/XXX.plist",
            f"{self.folder}/layout/Library/PreferenceLoader/Preferences/{self.name}.plist",
        )
        # format plists
        content = open(
            f"{self.folder}/layout/Library/PreferenceLoader/Preferences/{self.name}.plist",
            "r",
        ).read()
        with open(
            f"{self.folder}/layout/Library/PreferenceLoader/Preferences/{self.name}.plist",
            "w",
        ) as f:
            content = content.replace("REPLACEWITHNAME", self.name)
            content = content.replace("REPLACEWITHPREFIX", self.prefix)
            content = content.replace("REPLACEWITHID", self.id)
            content = content.replace("REPLACEWITHCLASS", f"{self.name}.RootListController")
            f.write(content)
        # info.plist
        content = open(f"{self.folder}/Resources/Info.plist", "r").read()
        with open(f"{self.folder}/Resources/Info.plist", "w") as f:
            content = content.replace("REPLACEWITHNAME", self.name)
            content = content.replace("REPLACEWITHPREFIX", self.prefix)
            content = content.replace("REPLACEWITHID", self.id)
            content = content.replace("REPLACEWITHCLASS", f"{self.name}.RootListController")
            f.write(content)
        # root.plist
        content = open(f"{self.folder}/Resources/Root.plist", "r").read()
        with open(f"{self.folder}/Resources/Root.plist", "w") as f:
            content = content.replace("REPLACEWITHNAME", self.name)
            content = content.replace("REPLACEWITHPREFIX", self.prefix)
            content = content.replace("REPLACEWITHID", self.id)
            content = content.replace("REPLACEWITHCLASS", f"{self.name}.RootListController")
            f.write(content)
