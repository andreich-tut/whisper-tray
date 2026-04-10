#!/usr/bin/env python3
"""Run all code quality checks for WhisperTray."""

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CHECK_PATHS = (REPO_ROOT / "whisper_tray", REPO_ROOT / "tests")


def _build_env() -> dict[str, str]:
    """Build an environment that prefers the repo virtualenv tools."""
    env = os.environ.copy()
    venv_bin = REPO_ROOT / "venv" / "bin"
    if venv_bin.is_dir():
        current_path = env.get("PATH", "")
        env["PATH"] = f"{venv_bin}{os.pathsep}{current_path}"
    return env


def run_command(cmd: list[str], description: str) -> bool:
    """Run a command and return True if it succeeded."""
    print(f"\n{'=' * 60}")
    print(f"  {description}")
    print(f"{'=' * 60}")
    print(f"  {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd, env=_build_env())
    if result.returncode != 0:
        print(f"\n❌ {description} FAILED")
        return False
    print(f"\n✅ {description} PASSED")
    return True


def run_black_check() -> bool:
    """Run Black formatting checks without shelling out to the hanging CLI."""
    print(f"\n{'=' * 60}")
    print("  Black (code formatting)")
    print(f"{'=' * 60}")
    print("  black --check whisper_tray/ tests/")
    print()

    try:
        import black
    except ImportError:
        print("\n❌ Black (code formatting) FAILED")
        print("  Unable to import the black package.")
        return False

    pyproject_config = black.parse_pyproject_toml(str(REPO_ROOT / "pyproject.toml"))
    target_versions = {
        black.TargetVersion[value.upper()]
        for value in pyproject_config.get("target_version", [])
        if value.upper() in black.TargetVersion.__members__
    }
    mode = black.FileMode(
        line_length=pyproject_config.get("line_length", black.DEFAULT_LINE_LENGTH),
        target_versions=target_versions,
    )

    reformatted_files: list[str] = []
    invalid_files: list[str] = []

    for base_path in CHECK_PATHS:
        for file_path in sorted(base_path.rglob("*.py")):
            source = file_path.read_text(encoding="utf-8")
            try:
                formatted = black.format_file_contents(source, fast=False, mode=mode)
            except black.NothingChanged:
                continue
            except black.InvalidInput as exc:
                invalid_files.append(f"{file_path.relative_to(REPO_ROOT)}: {exc}")
                continue

            if formatted != source:
                reformatted_files.append(str(file_path.relative_to(REPO_ROOT)))

    if invalid_files or reformatted_files:
        for line in invalid_files:
            print(f"  {line}")
        for line in reformatted_files:
            print(f"  would reformat {line}")
        print("\n❌ Black (code formatting) FAILED")
        return False

    file_count = sum(1 for base_path in CHECK_PATHS for _ in base_path.rglob("*.py"))
    print(f"All done! {file_count} files would be left unchanged.")
    print("\n✅ Black (code formatting) PASSED")
    return True


def main() -> None:
    """Run all quality checks."""
    print("WhisperTray - Running all code quality checks...")

    results = []

    # 1. Black - code formatting
    results.append(run_black_check())

    # 2. isort - import sorting
    results.append(
        run_command(
            ["isort", "--check-only", "whisper_tray/", "tests/"],
            "isort (import sorting)",
        )
    )

    # 3. flake8 - linting
    results.append(
        run_command(
            ["flake8", "whisper_tray/", "tests/", "--max-line-length=88"],
            "flake8 (linting)",
        )
    )

    # 4. mypy - type checking
    results.append(run_command(["mypy", "whisper_tray/"], "mypy (type checking)"))

    # 5. bandit - security scanning
    results.append(
        run_command(["bandit", "-r", "whisper_tray/"], "bandit (security scan)")
    )

    # 6. pytest - run tests
    results.append(run_command(["pytest"], "pytest (unit tests)"))

    # Summary
    print(f"\n{'=' * 60}")
    print("  SUMMARY")
    print(f"{'=' * 60}")

    checks = [
        "Black (formatting)",
        "isort (imports)",
        "flake8 (linting)",
        "mypy (types)",
        "bandit (security)",
        "pytest (tests)",
    ]

    for check, passed in zip(checks, results):
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {check:.<40} {status}")

    print()
    if all(results):
        print("🎉 All checks passed!")
        sys.exit(0)
    else:
        failed_count = sum(1 for r in results if not r)
        print(f"💥 {failed_count} check(s) failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
