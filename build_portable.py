"""
Automated build script to compile Office Time Widget into a portable Windows executable (.exe).
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

from create_icon import generate_icons


def build():
    root_dir = Path(__file__).parent.resolve()
    os.chdir(str(root_dir))

    print("=" * 60)
    print("  Building Portable Windows Office Time Widget (.EXE)")
    print("=" * 60)

    # 1. Ensure Icon Assets are generated
    resources_dir = root_dir / "resources"
    ico_path, png_path = generate_icons(resources_dir)

    # 2. Clean previous build artifacts
    build_dir = root_dir / "build"
    dist_dir = root_dir / "dist"

    # 3. Execute PyInstaller
    spec_path = root_dir / "OfficeTimeWidget.spec"
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "-y",
        str(spec_path),
    ]

    print(f"Running PyInstaller command: {' '.join(cmd)}")
    res = subprocess.run(cmd, capture_output=False)

    if res.returncode != 0:
        print("\n[ERROR] PyInstaller build failed with return code:", res.returncode)
        sys.exit(res.returncode)

    exe_path = dist_dir / "OfficeTimeWidget.exe"
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print("\n" + "=" * 60)
        print("  [SUCCESS] Portable Build Completed Successfully!")
        print(f"  Executable: {exe_path}")
        print(f"  File Size:  {size_mb:.2f} MB")
        print("=" * 60)
    else:
        print("\n[WARNING] Executable not found at expected location:", exe_path)


if __name__ == "__main__":
    build()
