"""Minimal native macOS command-line build fixture for Luz."""

from luz import Meta, Module


meta = Meta(
    # Build a release executable for the host's Apple Silicon macOS SDK.
    debug=False,
    release=True,
    platform="macosx",
    archs=["arm64"],
    min_vers="14.0",
    # This fixture tests compilation only, so it intentionally does not create
    # a Debian package or stage files in a device filesystem layout.
    pack=False,
    rootless=False,
)

modules = [
    Module(
        name="luz-mac-test",
        type="tool",
        files=["Sources/main.c"],
        # A simple C program needs no third-party runtime library.
        libraries=[],
    )
]
