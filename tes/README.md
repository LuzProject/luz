# Luz macOS command-line build fixture

This project builds a minimal native arm64 macOS command-line executable. It
exercises Luz's SDK discovery, C compilation, linking, and code-signing path
without requiring iOS packaging or a hooking runtime.

From the repository root, run this command to force Python to use this local
checkout rather than an older globally installed `luz` executable:

```sh
python3 -m luz build --clean --path tes
```

Alternatively, reinstall the checkout in editable mode before using `luz`:

```sh
python3 -m pip install --editable .
```

On success, run the executable:

```sh
tes/.luz/bin/luz-mac-test/luz-mac-test
```

The project requires Xcode (or its Command Line Tools) and `ldid`. It targets
macOS 14+ on Apple Silicon. The generated `.luz/` directory is ignored.
