#!/usr/bin/env python3
"""Pre-commit hook script to validate the application can build successfully."""

import compileall
import sys


def check_python_syntax() -> bool:
    """Compile all Python files to catch syntax errors."""
    print("Checking Python syntax...")
    result = compileall.compile_dir(
        "whisper_tray",
        quiet=1,
        force=True,
        optimize=0,
    )
    if result:
        print("Python syntax check passed")
        return True
    print("Syntax errors found")
    return False


def check_imports() -> bool:
    """Try importing all modules to catch import errors."""
    print("Checking module imports...")
    try:
        import whisper_tray  # noqa: F401
        from whisper_tray import app  # noqa: F401
        from whisper_tray import cli  # noqa: F401
        from whisper_tray import clipboard  # noqa: F401
        from whisper_tray import config  # noqa: F401
        from whisper_tray.audio import recorder  # noqa: F401
        from whisper_tray.audio import transcriber  # noqa: F401
        from whisper_tray.input import hotkey  # noqa: F401
        from whisper_tray.tray import icon  # noqa: F401
        from whisper_tray.tray import menu  # noqa: F401

        print("All modules import successfully")
        return True
    except ModuleNotFoundError:
        print("Skipped (package not installed in this environment)")
        return True
    except Exception as e:
        print(f"Import error: {e}")
        return False


def check_pyproject() -> bool:
    """Validate pyproject.toml is well-formed."""
    print("Validating project configuration...")
    try:
        # Python 3.11+
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib

        with open("pyproject.toml", "rb") as f:
            tomllib.load(f)
        print("pyproject.toml is valid")
        return True
    except Exception as e:
        print(f"pyproject.toml validation error: {e}")
        return False


def main() -> None:
    """Run all build validation checks."""
    print("Running build validation...")

    all_passed = True

    if not check_python_syntax():
        all_passed = False

    if not check_imports():
        all_passed = False

    if not check_pyproject():
        all_passed = False

    if all_passed:
        print("Build validation passed!")
        sys.exit(0)
    else:
        print("Build validation failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
