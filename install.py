# module imports
from argparse import ArgumentParser
from curses import wrapper
from os import environ, getuid
from pathlib import Path
from platform import platform
from pkg_resources import working_set
from shutil import which
from subprocess import getoutput
from typing import Union


if getuid() != 0:
    print("[INSTALLER] Please run this script as root.")
    exit(1)


required = {"luz"}
installed = {pkg.key for pkg in working_set}
missing = required - installed


if not missing:
    print("[INSTALLER] luz is already installed.")
    exit(0)


def should_install_deps(win, nti):
    win.nodelay(True)
    win.addstr('[INSTALLER] The following dependencies are missing: {}\n[INSTALLER] Press "y" to install them now.'.format(", ".join(nti)))
    key = ""
    while 1:
        try:
            key = win.getkey()
            if key == "y":
                return True
            else:
                return False
        except Exception as e:
            # No input
            pass


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


# installer
def check_for_deps() -> list:
    DEPLIST = ["git", "ldid", "xz"]
    need_to_install = []
    for dep in DEPLIST:
        if cmd_in_path(dep) is None:
            need_to_install.append(dep)
    return need_to_install


def get_manager() -> str:
    if cmd_in_path("apt") is not None:
        return "apt"
    elif cmd_in_path("brew") is not None:
        return "brew"
    elif cmd_in_path("pacman") is not None:
        return "pacman"
    elif cmd_in_path("dnf") is not None:
        return "dnf"
    elif cmd_in_path("yum") is not None:
        return "yum"
    else:
        return ""


def get_sdks():
    sdk_path = f"{PATH}/sdks"
    print("[INSTALLER] Downloading iOS SDKs... (this may take a while)")
    res = getoutput(
        f'sudo --user "{environ.get("SUDO_USER")}" mkdir -p {sdk_path} && sudo --user "{environ.get("SUDO_USER")}" {cmd_in_path("git")} clone https://github.com/xybp888/iOS-SDKs.git {sdk_path}'
    )


def darwin_install():
    xcpath = getoutput(f'{cmd_in_path("xcode-select")} -p')
    if not xcpath.endswith(".app/Contents/Developer"):
        print("[INSTALLER] Luz depends on both Xcode and the Xcode Command Line Tools.")
        exit(1)


def main():
    parser = ArgumentParser()
    parser.add_argument("-nd", "--no-deps", action="store_true", help="Do not install dependencies.")
    parser.add_argument("-r", "--ref", type=str, default="main", help="Reference tag of Luz to install.")

    args = parser.parse_args()

    platform_str = platform()
    if platform_str.startswith("Darwin") or platform_str.startswith("macOS"):
        darwin_install()
    elif platform_str.startswith("Linux"):
        pass
    else:
        print(f"[INSTALLER] Luz is not supported on this platform. ({platform_str})")
        exit(1)

    if not args.no_deps:
        need_to_install = check_for_deps()
        if need_to_install:
            should_install = wrapper(should_install_deps, need_to_install)
            if not should_install:
                print(f'[INSTALLER] Missing dependencies: {" ".join(need_to_install)}')
                print("[INSTALLER] Please install the missing dependencies before continuing.")
                exit(1)
            else:
                print("[INSTALLER] Installing dependencies...")
                manager = get_manager()
                if manager == "":
                    print("[INSTALLER] Could not find a package manager.")
                    print("[INSTALLER] Please install the missing dependencies before continuing.")
                    exit(1)
                else:
                    try:
                        res = getoutput(f'sudo {manager} install -y {" ".join(need_to_install)}')
                    except Exception as e:
                        print(f"[INSTALLER] Failed to install dependencies: {e}")
                        exit(1)
                print("[INSTALLER] Dependencies installed.")

    get_sdks()

    print("[INSTALLER] Installing luz...")
    try:
        res = getoutput(f'sudo --user "{environ.get("SUDO_USER")}" {cmd_in_path("pip")} install https://github.com/LuzProject/luz/archive/refs/heads/{args.ref}.zip')
    except Exception as e:
        print(f"[INSTALLER] Failed to install luz: {e}")
        exit(1)

    print("[INSTALLER] luz has been installed.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("[INSTALLER] Installation cancelled.")
        exit(1)
