# Copyright (c) 2026 Jaidan Arenas
# module imports
from os import makedirs
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from shlex import quote
from sys import modules
from threading import Lock

# local imports
from .logger import error, log_stdout, remove_log_stdout
from .utils import resolve_path

_pylogos_module = None
_pylogos_lock = Lock()


def clone_logos(module, update: bool = False) -> Path:
    """Clones pyLogos, the native Python Logos interpreter.

    :param Tweak module: The module to use logos on.
    :param bool update: Whether to update logos or not.
    :return: Path to logos dir
    """
    # Keep the requested SSH remote so private-key GitHub authentication works
    # in the same way as other Luz vendor dependencies.
    logos_url = "https://github.com/iCrazeiOS/pyLogos"
    storage = module.meta.storage
    # logos path
    logos_path = resolve_path(f"{storage}/vendor/pyLogos")
    # if it doesn't exist, clone logos
    if not logos_path.exists():
        log_stdout("Cloning pyLogos...")
        makedirs(logos_path.parent, exist_ok=True)
        module.cmd.exec_output(f"{quote(str(module.meta.git))} clone {quote(logos_url)} {quote(str(logos_path))} --recursive")
        remove_log_stdout("Cloning pyLogos...")
    # update
    if update:
        log_stdout("Updating pyLogos...")
        module.cmd.exec_output(f"cd {quote(str(logos_path))} && {quote(str(module.meta.git))} pull --ff-only")
        remove_log_stdout("Updating pyLogos...")
    # return path
    return logos_path


def load_pylogos(module):
    """Load Luz's vendored pyLogos module once for in-process preprocessing.

    The vendor checkout is deliberately loaded from its file path rather than
    added permanently to Luz's import namespace.  That lets ``pyLogos`` keep
    its own ``Logos`` package while avoiding a dependency on a globally
    installed package.

    Args:
        module: Luz project whose metadata locates the vendor directory.

    Returns:
        The loaded ``logos.py`` module exposing ``preprocess_file``.

    Raises:
        RuntimeError: If the vendor checkout does not provide the callable
            API required by this version of Luz.
    """
    global _pylogos_module
    with _pylogos_lock:
        if _pylogos_module is not None:
            return _pylogos_module

        logos_path = clone_logos(module)
        logos_file = logos_path / "logos.py"
        spec = spec_from_file_location("_luz_vendor_pylogos", logos_file)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Could not load vendored pyLogos at {logos_file}.")

        loaded = module_from_spec(spec)
        modules[spec.name] = loaded
        spec.loader.exec_module(loaded)
        if not hasattr(loaded, "preprocess_file"):
            raise RuntimeError("Vendored pyLogos is missing preprocess_file(). Update " "~/.luz/vendor/pyLogos to a version with the callable API.")
        _pylogos_module = loaded
        return _pylogos_module


def clone_libraries(module, update: bool = False) -> Path:
    """Clones the default Theos libraries.

    :param Module module: The module to clone libraries for
    :param bool update: Whether to update libraries or not.
    :return: Path to libraries dir
    """
    libraries_url = "--branch https://github.com/theos/lib"
    storage = module.meta.storage
    # libraries path
    libraries_path = resolve_path(f"{storage}/vendor/lib")
    # if it doesn't exist, clone logos
    if not libraries_path.exists():
        log_stdout("Cloning libraries...")
        makedirs(libraries_path.parent, exist_ok=True)
        module.cmd.exec_no_output(f"{module.meta.git} clone {libraries_url} {libraries_path} --recursive")
        remove_log_stdout("Cloning libraries...")
    # update
    if update:
        log_stdout("Updating libraries...")
        module.cmd.exec_no_output(f"cd {libraries_path} && {module.meta.git} pull")
        remove_log_stdout("Updating libraries...")
    # return path
    return libraries_path


def clone_headers(module, update: bool = False) -> Path:
    """Clones the default Theos headers.

    :param Module module: The module to clone headers for.
    :param bool update: Whether to update headers or not.
    :return: Path to headers dir
    """
    headers_url = "https://github.com/theos/headers"
    storage = module.meta.storage
    # headers path
    headers_path = resolve_path(f"{storage}/vendor/headers")
    # if it doesn't exist, clone logos
    if not headers_path.exists():
        log_stdout("Cloning headers...")
        makedirs(headers_path.parent, exist_ok=True)
        module.cmd.exec_no_output(f"{module.meta.git} clone {headers_url} {headers_path} --recursive")
        remove_log_stdout("Cloning headers...")
    # update
    if update:
        log_stdout("Updating headers...")
        module.cmd.exec_no_output(f"cd {headers_path} && {module.meta.git} pull")
        remove_log_stdout("Updating headers...")
    # return path
    return headers_path


def logos(luz, module, files: list) -> list:
    """Use logos on the specified files.

    :param Tweak luz: The module to use logos on.
    :param list files: The files to use logos on.
    :return: The list of logos'd files.
    """
    dir = luz.meta.luz_dir
    # Load pyLogos lazily: ordinary C/Objective-C/Swift modules should not
    # pay even the import cost of a Logos parser.
    pylogos = None
    # new files
    new_files = []

    for file in files:
        # declare output var
        output = f'{dir}/logos-processed/{str(file).split("/")[-1]}'
        # match to case
        file_formatted = str(file).split("/")[-1].split(".")[-1]
        if file_formatted == "x" or file_formatted == "xm":
            if pylogos is None:
                # pyLogos is imported from Luz's vendored checkout and called
                # directly. This removes a Python subprocess per Logos file.
                pylogos = load_pylogos(luz)
            try:
                output_value = pylogos.preprocess_file(file)
            except pylogos.LogosError as exc:
                error(f"pyLogos Error: {exc}", f"{module.abbreviated_name}")
                raise RuntimeError(str(exc)) from exc
            output_file = resolve_path(f"{output}.{'m' if file_formatted == 'x' else 'mm'}")
            output_file.parent.mkdir(parents=True, exist_ok=True)
            spl = output_value.splitlines()
            # Valid pyLogos output begins with a source line directive. Reject
            # empty or diagnostic-only output before handing it to clang.
            if not spl or not spl[0].startswith("#"):
                message = spl[0] if spl else "pyLogos did not produce output."
                error(f"pyLogos Error: {message}", f"{module.abbreviated_name}")
                raise RuntimeError(message)
            with open(output_file, "w") as f:
                f.write(output_value)
            new_files.append(
                {
                    "logos": True,
                    "new_path": output_file,
                    "old_path": resolve_path(file),
                }
            )
        else:
            new_files.append({"logos": False, "path": resolve_path(file)})

    # return files
    return new_files
