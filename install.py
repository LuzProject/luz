# module imports
from argparse import ArgumentParser
from os import environ, getuid, makedirs
from pathlib import Path
from platform import platform
from pkg_resources import working_set
from shutil import which
from subprocess import getoutput
from typing import Union


platform_str = platform()


if getuid() == 0:
    print("[INSTALLER] Please don't run this script as root.")
    exit(1)


required = {"luz"}
installed = {pkg.key for pkg in working_set}
missing = required - installed


if not missing:
    print("[INSTALLER] luz is already installed.")
    exit(0)


def should_install_deps(win, nti):
    win.nodelay(True)
    win.addstr(
        '[INSTALLER] The following dependencies are missing: {}\n[INSTALLER] Press "y" to install them now.'.format(
            ", ".join(nti)
        )
    )
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
    if (
        not resolve_path(sdk_path).exists()
        or len(resolve_path(f"{sdk_path}/*.sdk")) == 0
    ):
        print("[INSTALLER] iOS SDKs not found. Downloading...")
        try:
            makedirs(sdk_path, exist_ok=True)
            res = getoutput(
                f"curl -L https://api.github.com/repos/theos/sdks/tarball -o sdks.tar.gz && TMP=$(mktemp -d) && tar -xvf sdks.tar.gz --strip=1 -C $TMP && mv $TMP/*.sdk {sdk_path} && rm -r sdks.tar.gz $TMP"
            )
        except Exception as e:
            print(f"[INSTALLER] Failed to download iOS SDKs: {e}")
            exit(1)


def darwin_install():
    xcpath = getoutput(f'{cmd_in_path("xcode-select")} -p')
    if not xcpath.endswith(".app/Contents/Developer"):
        print("[INSTALLER] Luz depends on both Xcode and the Xcode Command Line Tools.")
        exit(1)
    manager = get_manager()
    print(
        "[INSTALLER] Installing dependencies. Please enter your password if prompted."
    )
    try:
        if manager == "apt":
            res = getoutput(
                f"sudo {manager} update && sudo {manager} install -y ldid xz-utils"
            )
        elif manager == "port":
            res = getoutput(
                f"sudo {manager} selfupdate && sudo {manager} install -y ldid xz"
            )
        elif manager == "brew":
            res = getoutput(f"{manager} update && {manager} install -y ldid xz")
        else:
            print("[INSTALLER] Could not find a package manager.")
            print(
                "[INSTALLER] Please install the missing dependencies before continuing."
            )
            exit(1)
    except Exception as e:
        print(f"[INSTALLER] Failed to install dependencies: {e}")
        exit(1)


def linux_install():
    manager = get_manager()
    print(
        "[INSTALLER] Installing dependencies. Please enter your password if prompted."
    )
    try:
        if manager == "apt":
            res = getoutput(
                f"sudo {manager} update && sudo {manager} install -y build-essential curl perl git"
            )
        elif manager == "pacman":
            res = getoutput(
                f"sudo {manager} -Syy && sudo {manager} -S --needed --noconfirm base-devel curl perl git"
            )
        elif manager == "dnf":
            res = getoutput(
                f'sudo {manager} check-update && sudo {manager} group install -y "C Development Tools and Libraries" && sudo {manager} install -y lzma libbsd curl perl git'
            )
        elif manager == "zypper":
            res = getoutput(
                f"sudo {manager} refresh && sudo {manager} install -y -t pattern devel_basis && sudo {manager} install -y libbsd0 curl perl git"
            )
        else:
            print("[INSTALLER] Could not find a package manager.")
            print(
                "[INSTALLER] Please install the missing dependencies before continuing."
            )
            exit(1)
    except Exception as e:
        print(f"[INSTALLER] Failed to install dependencies: {e}")
        exit(1)

    toolchain_path = f"{PATH}/toolchain"
    if (
        not resolve_path(toolchain_path).exists()
        or len(resolve_path(f"{toolchain_path}/*.toolchain")) == 0
    ):
        print("[INSTALLER] iOS toolchain not found. Downloading...")
        try:
            if manager == "apt":
                res = getoutput(f"sudo {manager} install -y libz3-dev zstd")
            elif manager == "pacman":
                res = getoutput(
                    f'sudo {manager} -S --needed --noconfirm libedit z3 zstd && LATEST_LIBZ3="$(ls -v /usr/lib/ | grep libz3 | tail -n 1)" && sudo ln -sf /usr/lib/$LATEST_LIBZ3 /usr/lib/libz3.so.4 && LATEST_LIBEDIT="$(ls -v /usr/lib/ | grep libedit | tail -n 1)" && sudo ln -sf /usr/lib/$LATEST_LIBEDIT /usr/lib/libedit.so.2'
                )
            elif manager == "dnf":
                res = getoutput(
                    f'sudo {manager} install -y z3-libs zstd && LATEST_LIBZ3="$(ls -v /usr/lib64/ | grep libz3 | tail -n 1)" && sudo ln -sf /usr/lib64/$LATEST_LIBZ3 /usr/lib64/libz3.so.4 && LATEST_LIBEDIT="$(ls -v /usr/lib64/ | grep libedit | tail -n 1)" && sudo ln -sf /usr/lib64/$LATEST_LIBEDIT /usr/lib64/libedit.so.2'
                )
            elif manager == "zypper":
                res = getoutput(
                    f'sudo {manager} install -y -y $(zypper search libz3 | tail -n 1 | cut -d "|" -f2) zstd && LATEST_LIBZ3="$(ls -v /usr/lib64/ | grep libz3 | tail -n 1)" && sudo ln -sf /usr/lib64/$LATEST_LIBZ3 /usr/lib64/libz3.so.4 && LATEST_LIBEDIT="$(ls -v /usr/lib64/ | grep libedit | tail -n 1)" && sudo ln -sf /usr/lib64/$LATEST_LIBEDIT /usr/lib64/libedit.so.2'
                )
        except Exception as e:
            print(f"[INSTALLER] Failed to install toolchain dependencies: {e}")
            exit(1)

        try:
            res = getoutput(
                f"curl -LO https://github.com/CRKatri/llvm-project/releases/download/swift-5.3.2-RELEASE/swift-5.3.2-RELEASE-ubuntu20.04.tar.zst && TMP=$(mktemp -d) && tar -xvf swift-5.3.2-RELEASE-ubuntu20.04.tar.zst -C $TMP && mkdir -p {toolchain_path}/linux/iphone {toolchain_path}/swift && mv $TMP/swift-5.3.2-RELEASE-ubuntu20.04/* {toolchain_path}/linux/iphone/ && ln -s {toolchain_path}/linux/iphone {toolchain_path}/swift && rm -r swift-5.3.2-RELEASE-ubuntu20.04.tar.zst $TMP"
            )
        except Exception as e:
            print(f"[INSTALLER] Failed to download toolchain: {e}")
            exit(1)


def main():
    parser = ArgumentParser()
    parser.add_argument(
        "-ns", "--no-sdks", action="store_true", help="Do not install SDKs."
    )
    parser.add_argument(
        "-r", "--ref", type=str, default="main", help="Reference tag of Luz to install."
    )

    args = parser.parse_args()

    if platform_str.startswith("Darwin") or platform_str.startswith("macOS"):
        darwin_install()
    elif platform_str.startswith("Linux"):
        linux_install()
    else:
        print(f"[INSTALLER] Luz is not supported on this platform. ({platform_str})")
        exit(1)

    if not args.no_sdks:
        get_sdks()

    print("[INSTALLER] Installing luz...")
    try:
        res = getoutput(
            f'{cmd_in_path("pip")} install https://github.com/LuzProject/luz/archive/refs/heads/{args.ref}.zip'
        )
    except Exception as e:
        print(f"[INSTALLER] Failed to install luz: {e}")
        exit(1)

    getoutput("mkdir -p ~/.luz/lib ~/.luz/headers")

    print("[INSTALLER] luz has been installed.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("[INSTALLER] Installation cancelled.")
        exit(1)
