Setup
---------------------

Installation
*********************

To install Luz, run the following command in your terminal:

.. code:: bash
    
    $ python -c "$(curl -fsSL https://install-luz.jaidan.dev)"

This will install Luz and all of its dependencies.

Luz requires Python 3.11 or newer. Logos source files are interpreted by the
native Python implementation, `pyLogos <https://github.com/iCrazeiOS/pyLogos>`_,
which Luz vendors under ``~/.luz/vendor/pyLogos`` and calls directly in the
Luz process. A separate Python subprocess is not launched for each Logos file.

Options
*********************

You can call the install script with the following options:

.. list-table::
   :widths: 5 1 10

   * - Option
     - Type
     - Description
   * - ``-ns``, ``--no-sdks``
     - Flag
     - Whether or not to install the SDKs. If this is set, you will need to install the SDKs manually.
   * - ``-r``, ``--ref``
     - String
     - Ref of Luz to install. This can be a branch, tag, or commit hash. Defaults to ``main``.

Updating an existing installation
*********************************

Once Luz is installed, update it directly instead of re-running the installer::

    luz update

Use ``luz update --ref <branch-or-tag>`` to select a GitHub reference, or
``luz update --no-vendors`` to leave vendored dependencies unchanged.
The bootstrap installer intentionally has no ``--update`` option.

Notes
*********************
 * If you are on Windows, you will need to install the Windows Subsystem for Linux (WSL). You can find instructions on how to do this `here <https://learn.microsoft.com/en-us/windows/wsl/install>`_.
 * If you are on macOS, you will need to install Xcode and the Xcode Command Line Tools.
