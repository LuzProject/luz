# module imports
from os import makedirs
from pathlib import Path
from shlex import quote
from sys import executable

# local imports
from .logger import error, log_stdout, remove_log_stdout
from .utils import resolve_path


def clone_logos(module, update: bool = False) -> Path:
    """Clones pyLogos, the native Python Logos interpreter.

    :param Tweak module: The module to use logos on.
    :param bool update: Whether to update logos or not.
    :return: Path to logos dir
    """
    # Keep the requested SSH remote so private-key GitHub authentication works
    # in the same way as other Luz vendor dependencies.
    logos_url = "git@github.com:iCrazeiOS/pyLogos.git"
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


def clone_libraries(module, update: bool = False) -> Path:
    """Clones the default Theos libraries.

    :param Module module: The module to clone libraries for
    :param bool update: Whether to update libraries or not.
    :return: Path to libraries dir
    """
    libraries_url = "--branch rootless https://github.com/elihwyma/lib"
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


def substrate_compatibility_library(module, libraries_path: Path) -> Path:
    """Create a current-TAPI substrate stub when a vendor checkout is legacy.

    Older jailbreak library bundles describe CydiaSubstrate with a pre-v4 TBD
    file using ``platform: iphoneos``. New Xcode TAPI rejects that spelling.
    The generated v4 stub preserves its exported symbols while declaring the
    current ``arm64-ios``/``arm64e-ios`` targets.
    """
    source = libraries_path / "libsubstrate.tbd"
    if not source.is_file() or "platform:        iphoneos" not in source.read_text():
        return libraries_path

    compatibility_dir = resolve_path(f"{module.meta.storage}/vendor/luz-compat")
    compatibility_dir.mkdir(parents=True, exist_ok=True)
    output = compatibility_dir / "libsubstrate.tbd"

    # Rebuild only when the vendor source changes; this avoids stale stubs
    # while keeping normal incremental builds fast.
    if not output.is_file() or output.stat().st_mtime < source.stat().st_mtime:
        converted = ["--- !tapi-tbd", "tbd-version: 4", "targets: [ arm64-ios, arm64e-ios ]"]
        for line in source.read_text().splitlines()[1:]:
            if line.startswith("archs:") or line.startswith("platform:"):
                continue
            if line.startswith("  - archs:"):
                converted.append("  - targets:         [ arm64-ios, arm64e-ios ]")
            else:
                converted.append(line)
        output.write_text("\n".join(converted) + "\n")
    return compatibility_dir


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
    # logos dir
    logos = clone_logos(luz)
    # pyLogos is a Python port of Theos Logos.  Use the same interpreter that
    # launched Luz so it works with current Python installations.
    logos_exec = logos / "logos.py"
    # new files
    new_files = []

    for file in files:
        # declare output var
        output = f'{dir}/logos-processed/{str(file).split("/")[-1]}'
        # match to case
        file_formatted = str(file).split("/")[-1].split(".")[-1]
        if file_formatted == "x" or file_formatted == "xm":
            # pyLogos emits translated Objective-C on stdout. Quoting every
            # component keeps source paths containing spaces safe for the shell.
            output_value = luz.cmd.exec_output(
                f"{quote(executable)} {quote(str(logos_exec))} {quote(str(file))}"
            ).decode()
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
