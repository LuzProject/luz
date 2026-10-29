import re


_PACKAGE_NAME = re.compile(r"^[a-z0-9][a-z0-9+.-]*$")
_ARCHITECTURE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]*$")


class Control:
    """Define Debian binary-package metadata written to ``DEBIAN/control``.

    Required fields are validated during configuration so package errors are
    reported before compiling.  List-valued relationship fields are emitted
    as comma-separated Debian control fields.  ``name`` and ``author`` are
    Luz conveniences; they are not serialized as non-standard control fields.
    """

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
        """Create validated metadata for the package being built.

        Args:
            id: Lowercase Debian package identifier, for example
                ``"com.example.my-tweak"``.
            version: Debian package version, for example ``"1.2.0-1"``.
            maintainer: Debian maintainer value, commonly ``"Name <email>"``.
            architecture: Debian architecture such as ``"iphoneos-arm64"``
                or ``"all"``; it must be one whitespace-free value.
            name: Human-readable Luz project name.  If ``description`` is
                omitted, this becomes the one-line Debian description.
            description: Debian package synopsis, optionally followed by
                long-description lines separated with newlines.  Blank lines
                are encoded using Debian's required `` .`` continuation.
            author: Luz-only author value; defaults to ``maintainer``.
            depends: Required package relationships, optionally including
                Debian version expressions such as ``"firmware (>= 15.0)"``.
            conflicts: Packages that cannot be installed alongside this one.
            replaces: Packages whose files this package may replace.
            provides: Virtual package names supplied by this package.
            recommends: Strong but non-mandatory dependencies.
            suggests: Optional related packages.
            breaks: Packages known to be incompatible with this version.
            enhances: Packages this package enhances.
            pre_depends: Dependencies that must be configured before unpack.
            essential: Mark the package as Debian ``Essential: yes``.
            original_maintainer: Upstream/original maintainer control field.
            uploaders: Additional Debian uploader identities.
            priority: Debian archive priority, such as ``"optional"``.
            section: Debian archive section, such as ``"Tweaks"``.
            homepage: Project homepage URL.

        Raises:
            ValueError: If a required field cannot be serialized safely as a
                Debian control field.
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
