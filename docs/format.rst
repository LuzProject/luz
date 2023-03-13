luzconf.py Formatting
---------------------

Luz uses a Python file to define the settings for the build. Python is used so that compile-time variables can be specified, much like a Makefile. The file is called ``luzconf.py`` and is located in the root of your project.

``LuzGen`` will automatically generate a ``luzconf.py`` file for any project that you create with it. It's not recommended to create your own ``luzconf.py``, and you should only do so if you know what you're doing.

Meta
*********************

This is where you define the settings for the build, such as the SDK, the architectures to build for, and the ``clang`` path.

Meta variables are defined in a class called ``Meta`` that can be imported from ``luz``.

.. list-table::
   :widths: 5 1 10

   * - Variable
     - Type
     - Description
   * - ``debug``
     - Boolean
     - Whether or not to build a debug version of the package. (``true`` if not specified)
   * - ``release``
     - Boolean
     - Whether or not to build a release version of the package. (``false`` if not specified)
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
     - Platform to build for. Can be ``macosx``, ``iphoneos`` or ``watchos``. (``iphoneos`` if not specified)
   * - ``min_vers``
     - String
     - Minimum version to build for. (``15.0`` if not specified)
    
Control
*********************

This is where you define the settings for the control file.

Control variables are defined in a class called ``Control`` that can be imported from ``luz``.

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

Additional control options can be found `here <https://github.com/LuzProject/luz/tree/main/luz/config/components/control.py#L26/>`_.

Scripts
*********************

This is where maintainer scripts are defined.

Scripts are defined in a class called ``Scripts`` that can be imported from ``luz``.

.. list-table::
   :widths: 5 1 10

   * - Variable
     - Type
     - Description
   * - ``type``
     - String
     - Type of script to run. Can be ``preinst``, ``postinst``, ``prerm``, ``postrm``.
   * - ``path``
     - String (Optional)
     - Path to the script to copy. (``None`` if not specified)
   * - ``content``
     - String (Optional)
     - Content of the script to copy. (``None`` if not specified)

Please note that either ``path`` or ``content`` must be specified. If both are specified, ``path`` will be used.

Modules
*********************

Modules are where you define the files to compile and the settings for the build.

Modules are defined in a class called ``Modules`` that can be imported from ``luz``.

.. list-table::
   :widths: 5 1 10

   * - Variable
     - Type
     - Description
   * - ``type``
     - String
     - Type of module to build. (``tweak`` if not specified)
   * - ``c_flags``
     - List
     - Flags to pass to ``clang`` when compiling C files.
   * - ``swift_flags``
     - List
     - Flags to pass to ``swift`` when compiling Swift files.
   * - ``linker_flags``
     - List
     - Flags to pass to the linker.
   * - ``optimization``
     - String
     - Optimization level to use for ``clang``. (``0`` if not specified)
   * - ``warnings``
     - List
     - Warnings flags to pass to ``clang``. (``["-Wall"]`` if not specified)
   * - ``ent_flags``
     - List
     - Entitlement flags to pass to ``ldid``. (``["-S"]`` if not specified)
   * - ``use_arc``
     - Boolean
     - Whether or not to use ARC for ``clang``. (``true`` if not specified)
   * - ``only_compile_changed``
     - Boolean
     - Whether or not to only compile changed files. (``true`` if not specified)
   * - ``bridging_headers``
     - List
     - List of bridging headers to use for ``swift``.
   * - ``frameworks``
     - List
     - List of frameworks to link against.
   * - ``private_frameworks``
     - List
     - List of private frameworks to link against.
   * - ``libraries``
     - List
     - List of libraries to link against.
   * - ``before_stage``
     - Callable
     - Function to run before staging.
   * - ``after_stage``
     - Callable
     - Function to run after staging.

Additional module options can be found `here <https://github.com/LuzProject/luz/tree/main/luz/config/components/module.py#L35/>`_.

Submodules
*********************

Submodules are where you define paths to directories with ``luz.py`` files to include in your project.

Submodules are defined in a class called ``Submodule`` that can be imported from ``luz``.

.. list-table::
   :widths: 5 1 10

   * - Variable
     - Type
     - Description
   * - ``path``
     - String
     - Path to the submodule.
   * - ``inherit``
     - String
     - Whether or not to inherit non-specified ``meta`` options from the parent project. (``true`` if not specified)

Example ``luzconf.py``
*********************


.. code:: Python

    from luz import Control, Meta, Modules, Submodule

    # define meta options
    meta = Meta(
        release=True,
        archs=['arm64', 'arm64e'],
        cc='/usr/bin/gcc',
        swift='/usr/bin/swift',
        compression='zstd',
        platform='iphoneos',
        sdk='~/.luz/sdks/iPhoneOS14.5.sdk',
        rootless=True,
        min_vers='15.0'
    )

    # define control options
    control = Control(
        id='com.jaidan.demo',
        name='LuzBuildDemo',
        author='Jaidan',
        description='LuzBuild demo',
        section='Tweaks',
        version='1.0.0',
        dependencies='firmware (>= 15.0), mobilesubstrate'
    )

    # define modules
    modules = [
        Module(
            filter={
              'bundles': ['com.apple.SpringBoard']
            },
            files=['Tweak.xm']
        )
    ]

    # define submodules
    submodules = [
        Submodule(path="./Preferences")
    ]
