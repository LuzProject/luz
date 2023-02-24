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
        depends: list = [],
        conflicts: list = [],
        replaces: list = [],
        provides: list = [],
        recommends: list = [],
        suggests: list = [],
        breaks: list = [],
        enhances: list = [],
        pre_depends: list = [],
        essential: bool = False,
        original_maintainer: str = None,
        uploaders: list = [],
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
        self.description = description
        self.version = version
        self.maintainer = maintainer
        self.author = author if author else maintainer
        self.architecture = architecture
        self.name = name
        self.depends = depends
        self.conflicts = conflicts
        self.replaces = replaces
        self.provides = provides
        self.recommends = recommends
        self.suggests = suggests
        self.breaks = breaks
        self.enhances = enhances
        self.pre_depends = pre_depends
        self.essential = essential
        self.original_maintainer = original_maintainer
        self.uploaders = uploaders
        self.priority = priority
        self.section = section
        self.homepage = homepage

        # make sure that necessary variables are set
        if not self.id or not self.version or not self.maintainer or not self.architecture:
            raise Exception("Missing necessary variables for control.")

        # get raw control
        self.raw = self.__str__()

    def __str__(self):
        """Returns the control's string representation.

        :return: The control's string representation.
        :rtype: str
        """
        # create string
        string = ""
        # loop through keys
        for key in self.__dict__:
            # raw
            if key == "raw":
                continue
            # get value
            value = self.__dict__[key]
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

                # check for id
                if key == "id":
                    string += f"Package: {value}\n"
                # otherwise, just add to the control
                else:
                    string += f"{key.capitalize().replace('_', '-')}: {value}\n"
        # return string
        return string
