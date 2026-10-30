# Copyright (c) 2026 Jaidan Arenas
# module imports
from platform import platform as plat
from subprocess import getoutput

# local imports
from ...common.utils import cmd_in_path, get_luz_storage, resolve_path, setup_luz_dir
from ...common import cfg

PLATFORMS = {
    "iphoneos": "iphoneos",
    "iphonesimulator": "iphonesimulator",
    "macosx": "macosx",
    "watchos": "watchos",
    "watchsimulator": "watchsimulator",
}

# ``ios`` is convenient in project configuration, while ``iphoneos`` remains
# the canonical value needed by xcrun's SDK lookup.
PLATFORM_ALIASES = {"ios": "iphoneos", "macos": "macosx", "mac": "macosx", "watch": "watchos"}


class Meta:
    """Describe the toolchain and destination shared by every module.

    ``Meta`` is normally the first object in a ``luzconf.py``.  It selects
    the Apple SDK, compiler executables, deployment target, architectures,
    package layout, and connection details used by :meth:`Luz.install`.
    Command-line ``-m`` overrides and inherited configurations are applied
    before platform validation, so values supplied there have the same
    semantics as values written in the configuration file.

    Platform names follow Xcode's SDK names.  ``"iphoneos"`` is the
    canonical physical-device platform; ``"ios"`` is accepted as a friendly
    alias and is normalized to ``"iphoneos"``.  Simulator projects must use
    ``"iphonesimulator"``.  Rootless layout and ``ldid`` signing apply only
    to physical-device builds; they are automatically disabled for macOS and
    Simulator targets.

    Attributes created after initialization:
        sdk: Resolved SDK directory selected from ``~/.luz/sdks`` or Xcode.
        platform: Normalized Xcode SDK name, never the ``"ios"`` alias.
        root_dir: Destination root inside Luz's package staging directory.
        staging_dir: Temporary package tree used by the current build.
        ldid: Path to ``ldid`` for device builds, otherwise ``None``.
    """

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
        archs: list = None,
        platform: str = "iphoneos",
        min_vers: str = "15.0",
        messages: bool = False,
        install_user: str = "root",
        install_ip: str = "localhost",
        install_port: int = 22,
    ):
        """Create the project-wide build configuration.

        Args:
            debug: Add debug information and use ``-O0``.  If both ``debug``
                and ``release`` are true, release takes precedence.
            release: Build an optimized release artifact.  This disables
                ``debug`` when both options are selected.
            sdk: Absolute SDK path or SDK directory name under
                ``~/.luz/sdks``.  Leave empty to select the closest locally
                cached SDK or ask Xcode through ``xcrun``.
            prefix: Directory containing a cross-toolchain.  It is normally
                empty on macOS, where Xcode tools are discovered from PATH.
            cc: C, Objective-C, and linker driver name or absolute path.
            swift: Swift compiler name or absolute path.
            rootless: Install device package files below ``/var/jb``.  This
                is ignored for simulator, macOS, and watch targets.
            compression: Debian control/data archive compression: ``"xz"``
                (default), ``"gzip"``, ``"bzip2"``, or ``"zstd"`` when a
                compatible zstd executable is available.
            pack: Produce a ``.deb`` after building.  Set false when a
                caller only needs compiled module artifacts.
            archs: Architectures to compile, such as ``["arm64"]`` or
                ``["arm64", "arm64e"]``.  The device default is the latter.
            platform: Xcode SDK platform.  Valid values are ``"iphoneos"``
                (also ``"ios"``), ``"iphonesimulator"``, ``"macosx"``
                (also ``"macos"``/``"mac"``), ``"watchos"`` (also
                ``"watch"``), and ``"watchsimulator"``.
            min_vers: Minimum OS version used in target triples and Clang
                deployment flags, for example ``"15.0"``.
            messages: Print full compiler and packaging commands.
            install_user: SSH account used by :meth:`Luz.install`.
            install_ip: Device hostname or IP address used by
                :meth:`Luz.install`; it does not affect local builds.
            install_port: SSH port used by :meth:`Luz.install`.

        Raises:
            ValueError: If ``platform`` is unsupported.
            Exception: If a requested toolchain, SDK, Git, or required
                device-signing tool cannot be found.
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
        self.archs = list(archs or ["arm64", "arm64e"])
        self.platform = platform
        self.rootless = rootless
        self.min_vers = min_vers
        self.messages = messages
        self.install_user = install_user
        self.install_ip = install_ip
        self.install_port = install_port

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

        # Normalize aliases after command-line overrides and inheritance so
        # ``Meta(platform='ios')`` and ``-m platform=ios`` behave alike.
        raw_platform = str(self.platform).lower()
        self.platform = PLATFORM_ALIASES.get(raw_platform, raw_platform)
        if self.platform not in PLATFORMS:
            valid = ", ".join([*PLATFORMS, *PLATFORM_ALIASES])
            raise ValueError(f"Unsupported platform '{raw_platform}'. Valid platforms: {valid}.")
        self.rootless = bool(self.rootless) if self.is_device else False

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

        # ldid is only required for binaries installed on a physical iOS
        # device. Native macOS and Simulator builds do not depend on it.
        self.ldid = None
        if self.is_device:
            self.ldid = cmd_in_path(f'{(str(self.prefix) + "/") if self.prefix is not None else ""}ldid')
            if self.ldid is None:
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

    def target_triple(self, architecture: str) -> str:
        """Return Clang's Apple target triple for one architecture.

        Args:
            architecture: Apple architecture such as ``"arm64"`` or
                ``"x86_64"``.

        Returns:
            A target such as ``"arm64-apple-ios15.0"`` or
            ``"arm64-apple-ios15.0-simulator"``.
        """
        if self.is_device:
            suffix = f"ios{self.min_vers}"
        elif self.platform == "iphonesimulator":
            suffix = f"ios{self.min_vers}-simulator"
        elif self.platform == "watchos":
            suffix = f"watchos{self.min_vers}"
        elif self.platform == "watchsimulator":
            suffix = f"watchos{self.min_vers}-simulator"
        else:
            suffix = f"macosx{self.min_vers}"
        return f"{architecture}-apple-{suffix}"

    @property
    def is_device(self) -> bool:
        """Whether this configuration builds for a physical iOS device.

        Use this instead of comparing ``platform`` to a literal.  It keeps
        code correct when user-facing aliases, SDK naming, and compiler
        target-triple spelling differ.
        """
        return self.platform == "iphoneos"

    @property
    def deployment_flag_platform(self) -> str:
        """Return the canonical spelling for Clang deployment-version flags.

        This is the platform component used to form flags such as
        ``-miphoneos-version-min=15.0``.  It is intentionally distinct from
        the lowercase ``ios`` spelling used inside an Apple target triple.
        """
        return PLATFORMS[self.platform]

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
