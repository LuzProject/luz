import re


_PACKAGE_NAME = re.compile(r"^[a-z0-9][a-z0-9+.-]*$")
_ARCHITECTURE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]*$")


class Control:
    def __init__(
        self,
        id: str,
        version: str,
        maintainer: str,
        architecture: str,
        name: str = None,
        description: str = None,
        author: str = None,
        depends: list = None,
        conflicts: list = None,
        replaces: list = None,
        provides: list = None,
        recommends: list = None,
        suggests: list = None,
        breaks: list = None,
        enhances: list = None,
        pre_depends: list = None,
        essential: bool = False,
        original_maintainer: str = None,
        uploaders: list = None,
        priority: str = None,
        section: str = None,
        homepage: str = None,
    ):
        """The project's control metadata.

        Args:
            id (str): ID of the package.
            version (str): Version of the package.
            maintainer (str): Maintainer of the package.
            architecture (str): Architecture of the package.
            name (str, optional): Name of the package. Defaults to None.
            description (str, optional): Description of the package. Defaults to None.
            author (str, optional): Author of the package. Defaults to the maintainer.
            depends (list, optional): Dependencies of the project. Defaults to [].
            conflicts (list, optional): Conflicts of the project. Defaults to [].
            replaces (list, optional): Replaces of the project. Defaults to [].
            provides (list, optional): Provides of the project. Defaults to [].
            recommends (list, optional): Recommends of the project. Defaults to [].
            suggests (list, optional): Suggests of the project. Defaults to [].
            breaks (list, optional): Breaks of the project. Defaults to [].
            enhances (list, optional): Enhances of the project. Defaults to [].
            pre_depends (list, optional): Pre-dependencies of the project. Defaults to [].
            essential (bool, optional): Whether the project is essential. Defaults to False.
            original_maintainer (str, optional): Original maintainer of the project. Defaults to None.
            uploaders (list, optional): Uploaders of the project. Defaults to [].
            priority (str, optional): Priority of the project. Defaults to None.
            section (str, optional): Section of the project. Defaults to None.
            homepage (str, optional): Homepage of the project. Defaults to None.
        """
        # assign variables
        self.id = id
        # Description is mandatory in a binary DEBIAN/control. Existing
        # projects that supplied only name use it as the package synopsis.
        self.description = description or name or id
        self.version = version
        self.maintainer = maintainer
        self.author = author if author else maintainer
        self.architecture = architecture
        self.name = name
        self.depends = list(depends or [])
        self.conflicts = list(conflicts or [])
        self.replaces = list(replaces or [])
        self.provides = list(provides or [])
        self.recommends = list(recommends or [])
        self.suggests = list(suggests or [])
        self.breaks = list(breaks or [])
        self.enhances = list(enhances or [])
        self.pre_depends = list(pre_depends or [])
        self.essential = essential
        self.original_maintainer = original_maintainer
        self.uploaders = list(uploaders or [])
        self.priority = priority
        self.section = section
        self.homepage = homepage

        # Validate the fields before packaging. This provides a clear Luz error
        # instead of a later, less actionable dpkg failure.
        if not self.id or not self.version or not self.maintainer or not self.architecture:
            raise Exception("Missing necessary variables for control.")
        if not _PACKAGE_NAME.fullmatch(self.id):
            raise ValueError("Package IDs must be lowercase Debian package names.")
        if any(char.isspace() for char in self.version):
            raise ValueError("Debian package versions cannot contain whitespace.")
        if not _ARCHITECTURE.fullmatch(self.architecture):
            raise ValueError("Architecture must be a single Debian architecture name.")
        if "\n" in self.maintainer:
            raise ValueError("Maintainer cannot contain a newline.")

    def __str__(self):
        """Returns the control's string representation.

        :return: The control's string representation.
        :rtype: str
        """
        # create string
        string = ""
        # Only binary-package control fields are written. ``name`` and
        # ``author`` are Luz conveniences, not Debian control fields.
        fields = (
            ("Package", self.id),
            ("Version", self.version),
            ("Maintainer", self.maintainer),
            ("Architecture", self.architecture),
            ("Depends", self.depends),
            ("Pre-Depends", self.pre_depends),
            ("Recommends", self.recommends),
            ("Suggests", self.suggests),
            ("Breaks", self.breaks),
            ("Conflicts", self.conflicts),
            ("Replaces", self.replaces),
            ("Provides", self.provides),
            ("Enhances", self.enhances),
            ("Essential", self.essential),
            ("Original-Maintainer", self.original_maintainer),
            ("Uploaders", self.uploaders),
            ("Priority", self.priority),
            ("Section", self.section),
            ("Homepage", self.homepage),
            ("Description", self.description),
        )
        for key, value in fields:
            # check if value is not None
            if value is not None:
                # check for list
                if isinstance(value, list):
                    # check if list is not empty
                    if value != []:
                        value = ", ".join(value)
                    else:
                        continue
                # check for bool
                elif isinstance(value, bool):
                    if value is False:
                        continue
                    value = "yes"

                # Debian continuation lines begin with a space; a single "."
                # represents a blank line in a long description.
                if key == "Description" and "\n" in value:
                    short, *long = value.splitlines()
                    value = short + "\n" + "\n".join(
                        f" {line}" if line else " ." for line in long
                    )
                string += f"{key}: {value}\n"
        # return string
        return string
