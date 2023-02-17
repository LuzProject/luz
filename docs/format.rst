LuzBuild Formatting
---------------------

Luz uses it's own YAML based formatting for it's build files. Each build setting has a designated key.

Meta
*********************

This is where you define the settings for the build, such as the SDK, the architectures to build for, and the ``clang`` path.

.. list-table::
   :widths: 5 1 10

   * - Variable
     - Type
     - Description
   * - ``sdk``
     - String
     - SDK path to use for building. (uses ``xcrun`` to find an SDK if not specified)
   * - ``prefix``
     - String
     - Prefix to use for compilation commands. (``/`` if not specified)
   * - ``cc``
     - String
     - Path to ``clang`` to use for compilation. (Finds ``clang`` in PATH if not specified)
   * - ``swift``
     - String
     - Path to ``swift`` to use for compilation. (Finds ``swift`` in PATH if not specified)
   * - ``rootless``
     - String
     - Whether or not to make a rootless DEB archive. (``true`` if not specified)
   * - ``compression``
     - String
     - Command to use to compress the DEB archive. (``xz`` if not specified)
   * - ``pack``
     - String
     - Whether or not to pack the DEB archive. (``true`` if not specified)
   * - ``archs``
     - List
     - List of architectures to build for. (``['arm64', 'arm64e']`` if not specified)
   * - ``platform``
     - String
     - Platform to build for. (``iphoneos`` if not specified)
   * - ``minVers``
     - String
     - Minimum version to build for. (``14.0`` if not specified)
    
Control
*********************

This is where you define the settings for the control file.

.. list-table::
   :widths: 5 1 10

   * - Variable
     - Type
     - Description
   * - ``id``
     - String
     - ID of the package.
   * - ``name``
     - String
     - Name of the package.
   * - ``author``
     - String
     - Author of the package.
   * - ``maintainer``
     - String
     - Maintainer of the package.
   * - ``version``
     - String
     - Version of the package.
   * - ``section``
     - String
     - Section of the package.
   * - ``dependencies``
     - String
     - Dependencies of the package.
   * - ``architecture``
     - String
     - Architecture of the package.
   * - ``description``
     - String
     - Description of the package.

Modules
*********************

This is where a dictionary of modules are defined.

.. list-table::
   :widths: 5 1 10

   * - Variable
     - Type
     - Description
   * - ``type``
     - String
     - Type of module to build. (``tweak`` if not specified)
   * - ``cflags``
     - String
     - Flags to pass to ``clang`` when compiling C files.
   * - ``swiftflags``
     - String
     - Flags to pass to ``swift`` when compiling Swift files.
   * - ``optimization``
     - String
     - Optimization level to use for ``clang``. (``0`` if not specified)
   * - ``warnings``
     - String
     - Warnings level to use for ``clang``. (``-Wall`` if not specified)
   * - ``entflag``
     - String
     - Entitlements flag to use for ``ldid``. (``-S`` if not specified)
   * - ``entfile``
     - String
     - Path to entitlements plist to use for ``ldid``.
   * - ``useArc``
     - Boolean
     - Whether or not to use ARC for ``clang``. (``true`` if not specified)
   * - ``onlyCompileChanged``
     - Boolean
     - Whether or not to only compile changed files. (``true`` if not specified)
   * - ``bridgingHeaders``
     - List
     - List of bridging headers to use for ``swift``.
   * - ``frameworks``
     - List
     - List of frameworks to link against.
   * - ``privateFrameworks``
     - List
     - List of private frameworks to link against.
   * - ``libraries``
     - List
     - List of libraries to link against.

Submodules
*********************

This is where an array of submodule paths are defined.

Example LuzBuild
*********************

.. code:: yaml

    meta:
        archs:
            - arm64
            - arm64e
        cc: /usr/bin/gcc
        swift: /usr/bin/swift
        compression: zstd
        platform: iphoneos
        rootless: true
        version: 13

    control:
        architecture: iphoneos-arm64
        author: Jaidan
        description: LuzBuild demo
        id: com.jaidan.demo
        name: LuzBuildDemo
        section: Tweaks
        version: 1.0.0
    
    modules:
        Tweak:
            files:
                - Tweak.xm

    submodules:
        - Preferences
