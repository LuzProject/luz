Setup
---------------------

Installation
*********************

To install Luz, run the following command in your terminal:

.. code:: bash
    
    $ python -c "$(curl -fsSL https://raw.githubusercontent.com/LuzProject/luz/main/install.py)"

This will install Luz and all of its dependencies.

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
     - Ref of ``luz`` to install. This can be a branch, tag, or commit hash. Defaults to ``main``.

Notes
*********************
 * If you are on Windows, you will need to install the Windows Subsystem for Linux (WSL). You can find instructions on how to do this `here <https://learn.microsoft.com/en-us/windows/wsl/install>`_.
 * If you are on macOS, you will need to install XCode and the XCode command line tools.