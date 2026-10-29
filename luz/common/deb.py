"""Minimal, standards-compliant Debian binary package writer.

This deliberately uses only the Python standard library so packaging continues
to work on new CPython releases without relying on an unmaintained packer.
"""

from io import BytesIO
from bz2 import compress as bz2_compress
from gzip import compress as gzip_compress
from lzma import compress as xz_compress
from pathlib import Path
from shutil import which
from subprocess import run
from tarfile import open as tar_open

# Every modern .deb is a System V ar archive. This eight-byte signature must
# be written before its three members: debian-binary, control, and data.
AR_MAGIC = b"!<arch>\n"


def _ar_member(name: str, payload: bytes) -> bytes:
    """Return one SysV ar member, as required by the .deb container format."""
    if len(name) > 15:
        raise ValueError(f"Debian archive member name is too long: {name}")
    # An ar member header is exactly 60 ASCII bytes. Debian expects the
    # member-name slash convention used by System V ar implementations.
    header = (f"{name + '/':<16}{0:<12}{0:<6}{0:<6}{0o100644:<8o}{len(payload):<10}`\n").encode("ascii")
    member = header + payload
    # ar members are aligned to even byte boundaries.
    return member + (b"\n" if len(member) % 2 else b"")


def _tar(root: Path, include_root: bool) -> bytes:
    """Create a tar archive from a staging tree."""
    stream = BytesIO()
    with tar_open(fileobj=stream, mode="w", format=1) as archive:
        # Sort paths so the archive layout is stable and easy to inspect.
        paths = sorted(root.rglob("*"), key=lambda path: path.as_posix())
        for path in paths:
            arcname = path.relative_to(root).as_posix()
            if include_root:
                arcname = f"./{arcname}"
            archive.add(path, arcname=arcname, recursive=False)
    return stream.getvalue()


def _compress(payload: bytes, algorithm: str) -> tuple[str, bytes]:
    """Compress a tar payload using a Debian-supported compressor."""
    algorithm = algorithm.lower()
    # These compressors are supplied by Python. zstd is handled below because
    # its command-line implementation is the portable option on Python 3.11.
    compressors = {
        "xz": ("xz", xz_compress),
        "gz": ("gz", gzip_compress),
        "gzip": ("gz", gzip_compress),
        "bz2": ("bz2", bz2_compress),
        "bzip2": ("bz2", bz2_compress),
    }
    if algorithm in compressors:
        extension, compressor = compressors[algorithm]
        return extension, compressor(payload)
    if algorithm == "zstd":
        zstd = which("zstd")
        if not zstd:
            raise RuntimeError("zstd compression requires the 'zstd' command-line tool.")
        result = run([zstd, "--quiet", "--stdout", "--compress"], input=payload, capture_output=True)
        if result.returncode:
            raise RuntimeError(result.stderr.decode().strip() or "zstd compression failed.")
        return "zst", result.stdout
    if algorithm in {"none", "tar"}:
        return "", payload
    raise ValueError(f"Unsupported Debian package compression: {algorithm}")


def build_deb(staging_dir: Path, output_path: Path, compression: str = "xz") -> None:
    """Build a Debian package using the version-2 ar container layout."""
    control_dir = staging_dir / "DEBIAN"
    control_file = control_dir / "control"
    if not control_file.is_file():
        raise FileNotFoundError("DEBIAN/control is required to build a package.")

    # Debian metadata and payload live in separate tar members; DEBIAN must
    # never appear in the data member installed on the target system.
    control_extension, control_payload = _compress(_tar(control_dir, include_root=False), compression)
    data_root = staging_dir
    data_payload_stream = BytesIO()
    with tar_open(fileobj=data_payload_stream, mode="w", format=1) as archive:
        for path in sorted(data_root.rglob("*"), key=lambda item: item.as_posix()):
            if control_dir == path or control_dir in path.parents:
                continue
            archive.add(path, arcname=f"./{path.relative_to(data_root).as_posix()}", recursive=False)

    data_extension, data_payload = _compress(data_payload_stream.getvalue(), compression)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # The prescribed member order allows dpkg to inspect metadata without
    # reading the (usually much larger) payload archive.
    with output_path.open("wb") as package:
        package.write(AR_MAGIC)
        package.write(_ar_member("debian-binary", b"2.0\n"))
        package.write(_ar_member(f"control.tar.{control_extension}" if control_extension else "control.tar", control_payload))
        package.write(_ar_member(f"data.tar.{data_extension}" if data_extension else "data.tar", data_payload))
