Commands
---------------------

Luz is a command line tool. It is used to create, build, run, and test Luz projects.

``build``
*********************

Builds the ``luzconf.py`` project in the working directory.

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
     - Install the completed ``.deb`` with SSH and ``dpkg -i``. Installation
       is supported only for physical iOS device targets.

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
     - The type of project to generate: ``tool``, ``tweak``, ``preferences``,
       ``library`` (or ``lib``), or ``framework`` (or ``fw``). (``tweak`` if not specified)

``update``
*********************

Updates the installed Luz package without re-running the bootstrap installer::

    luz update

By default it uses Luz's normal vendor dependency update paths for
``headers``, ``lib``, and ``pyLogos`` under ``~/.luz/vendor``. A vendor
checkout with local changes is left untouched rather than overwritten.

.. list-table::
   :widths: 5 1 10

   * - Option
     - Type
     - Description
   * - ``-r`` / ``--ref``
     - String
     - GitHub branch, tag, or commit to install. Defaults to ``main``.
   * - ``--no-vendors``
     - Flag
     - Update Luz itself without updating vendored repositories.

Simulator builds
*********************

Set ``platform='iphonesimulator'`` in ``Meta`` to compile for an iOS Simulator.
Luz produces an arm64 Simulator Mach-O for tool modules; launching it still
requires packaging the tool into an iOS app bundle and installing that app with
Xcode or ``simctl``. Tweak and Preferences modules require a jailbreak runtime
and PreferenceLoader, so they cannot be launched in a stock Simulator.

Build speed
*********************

Luz caches source hashes and reuses unchanged object files by default. Avoid
``--clean`` during ordinary iteration: it intentionally removes that cache.
Compiler processes for changed files and requested architectures run in
parallel, with one worker per changed source/architecture pair by default.
Set ``Meta(jobs=...)`` to apply a shared process budget when intentionally
trading peak throughput for lower machine contention. Linking and packaging
remain ordered steps. A one-architecture build also skips ``lipo``.

For faster development builds, build only the architectures you need and avoid
package creation when it is not useful::

    meta = Meta(archs=['arm64'], compression='gzip', pack=False, jobs=4)

``arm64e`` is useful only when the target devices need it; including it adds a
second compile and link slice. ``gzip`` is faster than the default ``xz`` for
development packages. Set ``pack=True`` again before producing a distributable
package. Install ``ccache`` to enable its default compiler-result cache, or
set ``compiler_cache=False`` when diagnosing compiler behavior.
