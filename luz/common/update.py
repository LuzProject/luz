# Copyright (c) 2026 Jaidan Arenas
"""Self-update support for an installed Luz command."""

from pathlib import Path
from subprocess import CalledProcessError, run
from sys import executable
from sysconfig import get_path
from types import SimpleNamespace
from urllib.parse import quote

from .deps import clone_headers, clone_libraries, clone_logos
from .logger import log, warn
from .utils import CMD, cmd_in_path, get_luz_storage

LUZ_UPDATE_REPOSITORY = "https://github.com/LuzProject/luz"


def _pip_args(ref: str) -> list[str]:
    """Return a pip command that upgrades Luz from one GitHub ref."""
    package_url = f"{LUZ_UPDATE_REPOSITORY}/archive/{quote(ref, safe='')}.zip"
    args = [executable, "-m", "pip", "install", "--upgrade"]
    # PEP 668 installations require this opt-in, while virtual environments
    # and pyenv installs do not. Add it only where it is needed.
    if Path(get_path("stdlib"), "EXTERNALLY-MANAGED").exists():
        args.append("--break-system-packages")
    return [*args, package_url]


def update_luz(ref: str = "main", update_vendors: bool = True) -> None:
    """Update the installed Luz package and optional vendor repositories.

    The running process remains on its current code until it exits; invoke
    ``luz`` again after this function returns to use the updated release.

    Args:
        ref: GitHub branch, tag, or commit to install. Defaults to ``"main"``.
        update_vendors: Fast-forward installed ``headers``, ``lib``, and
            ``pyLogos`` vendor repositories when present. A vendor checkout
            with local work is left untouched and reported as a warning.

    Raises:
        RuntimeError: If pip cannot install the requested Luz reference.
    """
    if not ref or any(char.isspace() for char in ref):
        raise ValueError("Update references must be non-empty and contain no whitespace.")

    storage = get_luz_storage()
    git = cmd_in_path("git")
    if update_vendors and git is not None:
        # Reuse the dependency helpers used by normal Luz builds. Besides
        # keeping clone/update behavior in one place, this also ensures a
        # missing vendor checkout is initialized consistently.
        updater = SimpleNamespace(
            meta=SimpleNamespace(storage=storage, git=git),
            cmd=CMD(lock=None, show_messages=False),
        )
        for name, dependency in (
            ("headers", clone_headers),
            ("libraries", clone_libraries),
            ("pyLogos", clone_logos),
        ):
            log(f"Updating vendored {name}...", "🔄")
            try:
                dependency(updater, update=True)
            except Exception:
                warn(f"Could not update vendored {name}; leaving it unchanged.")
    elif update_vendors:
        warn("Git was not found; skipping vendored dependency updates.")

    log(f"Updating Luz from {ref}...", "🔄")
    try:
        run(_pip_args(ref), check=True)
    except CalledProcessError as exc:
        raise RuntimeError(f"Could not update Luz from '{ref}'.") from exc
    log("Luz has been updated. Run `luz` again to use the new version.", "✅")
