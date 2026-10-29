Commands
---------------------

Luz is a command line tool. It is used to create, build, run, and test Luz projects.

``build``
*********************

Builds a project using the LuzBuild in the working directory.

.. list-table::
   :widths: 5 1 10

   * - Option
     - Type
     - Description
   * - ``-c`` / ``--clean``
     - Flag
     - Whether or not to clean the build directory before building.
   * - ``-p`` / ``--path``
     - Flag
     - Path to the directory to build. (i.e. ``luz build -p /path/to/project``, defaults to the current working directory)
   * - ``-m`` / ``--meta``
     - Flag
     - Add meta information to the build. (i.e. ``luz build -m release=true``)
   * - ``-i`` / ``---install``
     - Flag
     - Whether or not to install the built project.

``verify``
*********************

Verifies the structure of ``luz.py``.

.. list-table::
   :widths: 5 1 10

   * - Option
     - Type
     - Description
   * - ``-p`` / ``--path``
     - Flag
     - Path to the directory to verify. (i.e. ``luz verify -p /path/to/project``, defaults to the current working directory)

``gen``
*********************

Generate a project.

.. list-table::
   :widths: 5 1 10

   * - Option
     - Type
     - Description
   * - ``-t`` / ``--type``
     - String
     - The type of project to generate: ``tool``, ``tweak``, or ``preferences``. (``tweak`` if not specified)

Simulator builds
*********************

Set ``platform='iphonesimulator'`` in ``Meta`` to compile for an iOS Simulator.
Luz produces an arm64 Simulator Mach-O for tool modules; launching it still
requires packaging the tool into an iOS app bundle and installing that app with
Xcode or ``simctl``.
