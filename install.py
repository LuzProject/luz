colors = {"black": "\033[30m", "red": "\033[31m", "green": "\033[32m", "darkgrey": "\033[90m", "reset": "\033[0m", "bold": "\033[01m"}


def log(message):
    print(colors["bold"] + colors["darkgrey"] + "[" + colors["reset"] + colors["bold"] + colors["green"] + "*" + colors["bold"] + colors["darkgrey"] + "] " + colors["reset"] + f"{message}")


def error(message):
    print(colors["bold"] + colors["darkgrey"] + "[" + colors["reset"] + colors["bold"] + colors["red"] + "!" + colors["bold"] + colors["darkgrey"] + "] " + colors["reset"] + f"{message}")


# module imports
try:
    from argparse import ArgumentParser
    from os import environ, getuid, makedirs
    from pathlib import Path
    from platform import platform
    from pkg_resources import working_set
    from shutil import which
    from subprocess import check_call, DEVNULL, getoutput
    from sys import executable
    from typing import Union
except:
    error("Failed to import required modules. Perhaps your Python installation is out of date?")
    error("Required modules: argparse, os, pathlib, platform, pkg_resources, shutil, subprocess, sys, typing")
    exit(1)

# check that python is 3.7 or higher
if not float(getoutput(f"{executable} --version | cut -d ' ' -f 2 | cut -d '.' -f 1,2")) < 3.7:
    error("Python 3.7 or higher is required to run this script.")
    exit(1)

# check that pip is installed
try:
    import pip
except:
    error("pip is not installed. Please install pip before running this script.")
    exit(1)


def command_wrapper(command: str) -> str:
    """Wrapper for commands to run in the shell.

    :param str command: The command to run.
    """
    return check_call(command, env=environ.copy(), shell=True, stdout=DEVNULL, stderr=DEVNULL)


# begin install script
platform_str = platform()

if getuid() == 0:
    print("Please don't run this script as root.")
    exit(1)


def resolve_path(path: str) -> Union[Path, list]:
    """Resolve a Path from a String."""
    # format env vars in path
    if "$" in str(path):
        path = format_path(path)
    # get path
    p = Path(path)
    # handle globbing
    if "*" in str(path):
        p = Path(path)
        parts = p.parts[1:] if p.is_absolute() else p.parts
        return list(Path(p.root).glob(str(Path("").joinpath(*parts))))
    # return path
    return p


def format_path(file: str) -> str:
    """Format a path that contains environment variables.

    :param str file: Path to format.
    :return: The formatted path.
    """
    new_file = ""
    for f in file.split("/"):
        if f.startswith("$"):
            new_file += environ.get(f[1:]) + "/"
        else:
            new_file += f + "/"
    return new_file


def cmd_in_path(cmd: str) -> Union[None, Path]:
    """Check if a command is in the path.

    :param str cmd: The command to check.
    :return: The path to the command, or None if it's not in the path."""
    path = which(cmd)

    if path is None:
        return None

    return resolve_path(path)


PATH = resolve_path(f'{environ.get("HOME")}/.luz')


def get_manager() -> str:
    if cmd_in_path("apt") is not None:
        return "apt"
    elif cmd_in_path("pacman") is not None:
        return "pacman"
    elif cmd_in_path("dnf") is not None:
        return "dnf"
    elif cmd_in_path("zypper") is not None:
        return "zypper"
    elif cmd_in_path("port") is not None:
        return "port"
    elif cmd_in_path("brew") is not None:
        return "brew"
    else:
        return ""


def get_sdks():
    sdk_path = f"{PATH}/sdks"
    if not resolve_path(sdk_path).exists() or len(resolve_path(f"{sdk_path}/*.sdk")) == 0:
        log("iOS SDKs not found. Downloading...")
        try:
            makedirs(sdk_path, exist_ok=True)
            command_wrapper(
                f"curl -L https://api.github.com/repos/theos/sdks/tarball -o sdks.tar.gz && TMP=$(mktemp -d) && tar -xf sdks.tar.gz --strip=1 -C $TMP && mv $TMP/*.sdk {sdk_path} && rm -r sdks.tar.gz $TMP"
            )
        except Exception as e:
            command_wrapper("rm -rf ./sdks.tar.gz")
            error("Failed to download iOS SDKs: " + str(e))
            exit(1)


def darwin_install():
    xcpath = getoutput(f'{cmd_in_path("xcode-select")} -p')
    if not xcpath.endswith(".app/Contents/Developer"):
        error("Xcode not found. Please install Xcode from the App Store.")
        exit(1)
    manager = get_manager()
    deps = ["ldid", "xz"]
    need = []
    for dep in deps:
        if cmd_in_path(dep) is None:
            need.append(dep)
    if need != []:
        log(f"Installing dependencies ({', '.join(need)}). Please enter your password if prompted.")
        try:
            if manager == "apt":
                command_wrapper(f"sudo {manager} update && sudo {manager} install -y ldid xz-utils")
            elif manager == "port":
                command_wrapper(f"sudo {manager} selfupdate && sudo {manager} install -y ldid xz")
            elif manager == "brew":
                command_wrapper(f"{manager} update && {manager} install -y ldid xz")
            else:
                error("Could not find a package manager.")
                error(f"Please install the missing dependencies before continuing. ({', '.join(need)})")
                exit(1)
        except Exception as e:
            error(f"Failed to install dependencies: {e}")
            exit(1)


def linux_install():
    manager = get_manager()
    deps = ["clang", "curl", "perl", "git"]
    need = []
    for dep in deps:
        if cmd_in_path(dep) is None:
            need.append(dep)
    if need != []:
        log(f"Installing dependencies ({', '.join(need)}). Please enter your password if prompted.")
        try:
            if manager == "apt":
                command_wrapper(f"sudo {manager} update && sudo {manager} install -y build-essential curl perl git")
            elif manager == "pacman":
                command_wrapper(f"sudo {manager} -Syy && sudo {manager} -S --needed --noconfirm base-devel curl perl git")
            elif manager == "dnf":
                command_wrapper(f'sudo {manager} check-update && sudo {manager} group install -y "C Development Tools and Libraries" && sudo {manager} install -y lzma libbsd curl perl git')
            elif manager == "zypper":
                command_wrapper(f"sudo {manager} refresh && sudo {manager} install -y -t pattern devel_basis && sudo {manager} install -y libbsd0 curl perl git")
            else:
                error("Could not find a package manager.")
                error(f"Please install the missing dependencies before continuing. ({', '.join(need)})")
                exit(1)
        except Exception as e:
            error(f"Failed to install dependencies: {e}")
            exit(1)

    toolchain_path = f"{PATH}/toolchain"
    if not resolve_path(toolchain_path).exists() or len(resolve_path(f"{toolchain_path}/linux/iphone/*")) == 0:
        log("iOS toolchain not found. Downloading...")
        arch = getoutput("uname -m")
        if arch == "arm64" or arch == "aarch64":
            toolchain_uri = "https://github.com/kabiroberai/swift-toolchain-linux/releases/download/v2.2.2/swift-5.7-ubuntu20.04-aarch64.tar.xz"
        else:
            toolchain_uri = "https://github.com/kabiroberai/swift-toolchain-linux/releases/download/v2.2.2/swift-5.7-ubuntu20.04.tar.xz"
        try:
            command_wrapper(f"curl -LO {toolchain_uri} && mkdir -p {toolchain_path} && tar -xf swift-5.7-ubuntu20.04*.tar.xz -C {toolchain_path} && rm -r swift-5.7-ubuntu20.04*.tar.xz $TMP")
        except Exception as e:
            command_wrapper("rm -rf swift-5.7-ubuntu20.04*.tar.xz")
            error(f"Failed to download toolchain: {e}")
            exit(1)


def main():
    parser = ArgumentParser()
    parser.add_argument("-ns", "--no-sdks", action="store_true", help="Do not install SDKs.")
    parser.add_argument("-u", "--update", action="store_true", help="Whether or not to update.")
    parser.add_argument("-r", "--ref", type=str, default="main", help="Reference tag of Luz to install.")

    args = parser.parse_args()

    required = {"luz"}
    installed = {pkg.key for pkg in working_set}
    missing = required - installed

    if not missing and not args.update:
        log("luz is already installed.")
        exit(0)
    elif missing and args.update:
        log("luz is not installed.")
        exit(0)

    if args.update:
        log("Updating vendor modules...")
        try:
            for module in ["headers", "lib", "logos"]:
                if resolve_path(f"$HOME/.luz/vendor/{module}").exists():
                    command_wrapper(f"cd ~/.luz/vendor/{module} && git pull")
        except Exception as e:
            error(f"Failed to update vendor modules: {e}")
            exit(1)

        log("Updating luz and its dependencies...")
        try:
            command_wrapper(f"{executable} -m pip uninstall -y luz pydeb pyclang && {executable} -m pip install https://github.com/LuzProject/luz/archive/refs/heads/{args.ref}.zip")
        except Exception as e:
            error(f"Failed to update luz: {e}")
            exit(1)

        log("luz has been updated.")
        exit(0)

    if platform_str.startswith("Darwin") or platform_str.startswith("macOS"):
        darwin_install()
    elif platform_str.startswith("Linux"):
        linux_install()
    else:
        error(f"Luz is not supported on this platform. ({platform_str})")
        exit(1)

    if not args.no_sdks:
        get_sdks()

    log("Installing luz...")
    try:
        command_wrapper(f"{executable} -m pip install https://github.com/LuzProject/luz/archive/refs/heads/{args.ref}.zip")
    except Exception as e:
        error(f"Failed to install luz: {e}")
        exit(1)

    command_wrapper(f"mkdir -p ~/.luz/lib ~/.luz/headers")

    log("luz has been installed.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        error("Operation cancelled.")
        exit(1)
