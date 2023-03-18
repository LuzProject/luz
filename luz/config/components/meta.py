# module imports
from platform import platform as plat
from subprocess import getoutput
from sys import argv

# local imports
from ...common.utils import cmd_in_path, get_luz_storage, resolve_path, setup_luz_dir
from ...common import cfg


class Meta:
    def __init__(
        self,
        debug: bool = True,
        release: bool = False,
        sdk: str = "",
        prefix: str = "",
        cc: str = "clang",
        swift: str = "swift",
        rootless: bool = True,
        compression: str = "xz",
        pack: bool = True,
        archs: list = ["arm64", "arm64e"],
        platform: str = "iphoneos",
        min_vers: str = "15.0",
    ):
        """Initialize Meta

        Args:
            debug (bool, optional): Debug (default: True)
            release (bool, optional): Release (default: False)
            sdk (str, optional): SDK to build with
            prefix (str, optional): Prefix to run commands with
            cc (str, optional): C compiler (default: clang)
            swift (str, optional): Swift compiler (default: swift)
            rootless (bool, optional): Rootless (default: True)
            compression (str, optional): Compression (default: xz)
            pack (bool, optional): Pack (default: True)
            archs (list, optional): Architectures to compile for (default: ['arm64', 'arm64e'])
            platform (str, optional): Platform (default: iphoneos)
            min_vers (str, optional): Minimum version (default: 15.0)
        """

        # assign variables
        self.debug = debug
        self.release = release
        self.sdk = sdk
        self.prefix = prefix
        self.cc = cc
        self.swift = swift
        self.compression = compression
        self.pack = pack
        self.archs = archs
        self.platform = platform
        self.rootless = rootless if platform == "iphoneos" else False
        self.min_vers = min_vers

        # handle passed config
        if cfg.passed != {}:
            for key, value in cfg.passed.items():
                self.__setattr__(key, value)

        if cfg.inherit is not None:
            luz = cfg.inherit

            # inherit
            for key, value in luz.meta.__dict__.items():
                if value != "" and value is not None and value != []:
                    setattr(self, key, getattr(luz.meta, key))

        # handle debug
        if self.debug and self.release:
            self.debug = False

        # storage
        self.storage = get_luz_storage()

        # luz dir
        self.luz_dir = setup_luz_dir()

        # staging dir
        self.staging_dir = self.luz_dir / "_"

        # root dir
        self.root_dir = self.staging_dir / ("var/jb" if self.rootless else "")

        # attempt to fetch prefix
        if self.prefix == "" and plat().startswith("Linux"):
            luz_prefix = resolve_path(f"{self.storage}/toolchain/linux/iphone/bin")
            if not luz_prefix.exists():
                raise Exception("Running on Linux, and toolchain is not installed.")
            self.prefix = luz_prefix

        # ensure prefix exists
        if self.prefix != "":
            self.prefix = resolve_path(self.prefix)
            if not self.prefix.exists():
                raise Exception("Specified prefix does not exist.")

        # get git
        self.git = cmd_in_path("git")
        if self.git is None:
            raise Exception("Git is needed in order to use Luz.")

        # format cc with prefix
        if self.prefix != "" and not resolve_path(self.cc).is_relative_to("/"):
            prefix_path = cmd_in_path(f"{self.prefix}/{self.cc}")
            if not prefix_path:
                raise Exception(f'C compiler "{self.cc}" not in prefix path.')
            self.cc = prefix_path

        # format swift with prefix
        if self.prefix != "" and not resolve_path(self.swift).is_relative_to("/"):
            prefix_path = cmd_in_path(f"{self.prefix}/{self.swift}")
            if not prefix_path:
                raise Exception(f'Swift compiler "{self.swift}" not in prefix path.')
            self.swift = prefix_path

        # format ldid with prefix
        self.ldid = cmd_in_path(f'{(str(self.prefix) + "/") if self.prefix is not None else ""}ldid')
        if self.ldid is None:
            # fall back to path
            self.ldid = cmd_in_path("ldid")
            if self.ldid is None:
                raise Exception("Could not find ldid.")

        # format ldid with prefix
        self.strip = cmd_in_path(f'{(str(self.prefix) + "/") if self.prefix is not None else ""}strip')
        if self.strip is None:
            # fall back to path
            self.strip = cmd_in_path("strip")
            if self.strip is None:
                raise Exception("Could not find strip.")

        # format lipo with prefix
        self.lipo = cmd_in_path(f'{(str(self.prefix) + "/") if self.prefix is not None else ""}lipo')
        if self.lipo is None:
            # fall back to path
            self.lipo = cmd_in_path("lipo")
            if self.lipo is None:
                raise Exception("Could not find lipo.")

        # attempt to manually find an sdk
        if self.sdk == "":
            self.sdk = self.__get_sdk()
        else:
            # ensure sdk exists
            self.sdk = resolve_path(self.sdk)
            if not self.sdk.exists():
                if resolve_path(f"{self.storage}/sdks/{self.sdk}").exists():
                    self.sdk = resolve_path(f"{self.storage}/sdks/{self.sdk}")
                else:
                    raise Exception("Specified SDK does not exist.")

    def __xcrun(self):
        xcrun = cmd_in_path("xcrun")
        if xcrun is None:
            raise Exception("xcrun not found.")
        else:
            sdkA = getoutput(f"{xcrun} --show-sdk-path --sdk {self.platform}").split("\n")[-1]
            if sdkA == "" or not sdkA.startswith("/"):
                raise Exception("Could not find an SDK.")
            self.sdk = sdkA
        return resolve_path(self.sdk)

    def __get_sdk(self):
        """Get an SDK from Xcode using xcrun."""
        sdks_path = resolve_path(f"{self.storage}/sdks")
        if sdks_path.exists():
            # get valid sdk paths that match the target platform
            valid_sdks = list(filter(lambda x: self.platform.lower() in x.name.lower(), sdks_path.iterdir()))
            # get the sdk that closest matches the minimum version
            if len(valid_sdks) == 0:
                return self.__xcrun()
            else:
                minimum = min(valid_sdks, key=lambda x: abs(float(str(x.name).lower().replace(self.platform.lower(), "").replace(".sdk", "")) - float(self.min_vers)))
                return minimum

        else:
            return self.__xcrun()
