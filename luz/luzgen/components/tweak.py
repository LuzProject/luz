# local imports
from ...common.logger import ask, error, log
from ...common.utils import resolve_path
from ..module import Module


class Tweak(Module):
    def __init__(self):
        # type
        self.type = "tweak"
        # valid source types
        self.VALID = ["logos", "objc", "c", "asm", "objcpp", "swift"]
        # srctype
        log(f"Valid source types: {', '.join(self.VALID)}")
        self.srctype = self.__ask_for("source type", "logos").lower()
        if self.srctype not in self.VALID:
            error(f'Invalid source type: {self.srctype}. Valid types: {", ".join(self.VALID)}')
            exit(1)

        # init super class
        super().__init__(self.type, self.srctype)

        # calculate ending
        if self.srctype == "logos":
            self.ending = ".x"
        elif self.srctype == "objc":
            self.ending = ".m"
        elif self.srctype == "c":
            self.ending = ".c"
        elif self.srctype == "asm":
            self.ending = ".s"
        elif self.srctype == "objcpp":
            self.ending = ".mm"
        elif self.srctype == "swift":
            self.ending = ".swift"

        # get keys
        self.name = self.__ask_for("name")

        # filter process
        self.filter = self.__ask_for("executable filter", "com.apple.springboard")

        # add values to dict
        self.dict.update({"modules": {"type": "tweak", "name": self.name, "files": [f"Sources/Tweak{self.ending}"], "filter": {"bundles": [self.filter]}}})

        # folder
        folder = resolve_path(
            self.__ask_for(
                "project folder",
                self.control["name"] if self.control is not None else self.name,
            )
        )

        # write to yaml
        self.write_to_file(folder)

    def __ask_for(self, key: str, default: str = None, dsc: str = "What", dsc1: str = "is") -> str:
        """Ask for a value.

        :param str key: The key to ask for.
        :param str default: The default value.
        :param str dsc: The descriptor of the question.
        :param str dsc1: The descriptor of the question.
        :return: The value.
        """
        if default is not None:
            val = ask(f'{dsc} {dsc1} this {self.type}\'s {key}? (enter for "{default}")')
            if val == "":
                return default
        else:
            val = ask(f"{dsc} {dsc1} this {self.type}'s {key}?")
            if val == "":
                error("You must enter a value.")
                val = ask(f"{dsc} {dsc1} this {self.type}'s {key}?")
        return val
