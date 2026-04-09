#!/usr/bin/env python3
"""Run all code quality checks for WhisperTray."""

import subprocess
import sys


def run_command(cmd: list[str], description: str) -> bool:
    """Run a command and return True if it succeeded."""
    print(f"\n{'=' * 60}")
    print(f"  {description}")
    print(f"{'=' * 60}")
    print(f"  {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"\n❌ {description} FAILED")
        return False
    print(f"\n✅ {description} PASSED")
    return True


def main() -> None:
    """Run all quality checks."""
    print("WhisperTray - Running all code quality checks...")

    results = []

    # 1. Black - code formatting
    results.append(
        run_command(
            ["black", "--check", "whisper_tray/", "tests/"],
            "Black (code formatting)",
        )
    )

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
