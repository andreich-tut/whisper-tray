#!/usr/bin/env python3
"""
Setup build directory structure by copying scripts to build/scripts/
This ensures build/scripts/ contains the canonical versions from scripts/
"""

import shutil
from pathlib import Path


def setup_build_scripts() -> bool:
    """Copy .bat files from scripts/ to build/scripts/"""
    project_root = Path(__file__).parent.parent
    scripts_dir = project_root / "scripts"
    build_scripts_dir = project_root / "build" / "scripts"

    if not scripts_dir.exists():
        print(f"ERROR: scripts directory not found at {scripts_dir}")
        return False

    # Create build/scripts if it doesn't exist
    build_scripts_dir.mkdir(parents=True, exist_ok=True)

    # Copy all .bat files
    bat_files = list(scripts_dir.glob("*.bat"))
    if not bat_files:
        print("WARNING: No .bat files found in scripts/")
        return True

    print(f"Copying {len(bat_files)} script(s) to build/scripts/...")
    for bat_file in bat_files:
        dest = build_scripts_dir / bat_file.name
        shutil.copy2(bat_file, dest)
        print(f"  ✓ {bat_file.name}")

    print("\nSUCCESS: Build scripts updated in build/scripts/")
    return True


if __name__ == "__main__":
    success = setup_build_scripts()
    exit(0 if success else 1)
