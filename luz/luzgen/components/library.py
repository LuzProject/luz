# Copyright (c) 2026 Jaidan Arenas
"""Interactive generator for reusable libraries and frameworks."""

from ...common.logger import ask, error, log
from ...common.utils import resolve_path
from ..module import Module


class Library(Module):
    """Generate a starter library project, optionally as a framework."""

    def __init__(self, module_type: str = "library"):
        self.type = module_type
        self.valid_sources = ("objc", "swift")
        log(f"Valid source types: {', '.join(self.valid_sources)}")
        self.source_type = self._ask_for("source type", "objc").lower()
        if self.source_type not in self.valid_sources:
            error(f"Invalid source type: {self.source_type}. " f"Valid types: {', '.join(self.valid_sources)}")
            raise ValueError("Unsupported LuzGen source type.")

        super().__init__(self.type, self.source_type)
        self.name = self._ask_for("name")
        source_file = "Library.m" if self.source_type == "objc" else "Library.swift"
        module = {
            "name": self.name,
            "type": self.type,
            "files": [f"Sources/{source_file}"],
        }
        if self.type == "framework" and self.source_type == "objc":
            module["public_headers"] = ["Sources/Framework.h"]
        self.dict["modules"] = module

        self.folder = resolve_path(
            self._ask_for(
                "folder for project",
                self.control["name"] if self.control is not None else self.name,
            )
        )
        self.write_to_file(self.folder)

    def after_untar(self) -> None:
        """Personalize the generated framework Info.plist when applicable."""
        if self.type != "framework":
            return
        info_plist = self.folder / "Resources" / "Info.plist"
        content = info_plist.read_text()
        content = content.replace("REPLACEWITHNAME", self.name)
        content = content.replace(
            "REPLACEWITHID",
            self.control["id"] if self.control is not None else f"com.yourcompany.{self.name.lower()}",
        )
        content = content.replace(
            "REPLACEWITHVERSION",
            self.control["version"] if self.control is not None else "1.0.0",
        )
        info_plist.write_text(content)

    def _ask_for(self, key: str, default: str = None) -> str:
        """Ask for a required generator setting with an optional default."""
        prompt = f"What is this {self.type}'s {key}?"
        if default is not None:
            value = ask(f'{prompt} (enter for "{default}")')
            return value or default
        value = ask(prompt)
        if value:
            return value
        error("You must enter a value.")
        return self._ask_for(key, default)
