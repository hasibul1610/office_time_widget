"""
Packaging script to generate a ready-to-publish, zero-dependency release ZIP
for deployment on computers without Python installed.
"""

import os
import shutil
import zipfile
from pathlib import Path


def create_publishable_release():
    root_dir = Path(__file__).parent.resolve()
    dist_exe = root_dir / "dist" / "OfficeTimeWidget.exe"

    if not dist_exe.exists():
        print(f"[ERROR] Executable not found at {dist_exe}. Please run build_portable.py first.")
        return

    release_root = root_dir / "release"
    release_root.mkdir(parents=True, exist_ok=True)

    package_folder_name = "OfficeTimeWidget_Portable_v1.0"
    package_dir = release_root / package_folder_name
    if package_dir.exists():
        shutil.rmtree(package_dir)
    package_dir.mkdir(parents=True, exist_ok=True)

    # 1. Copy Executable
    target_exe = package_dir / "OfficeTimeWidget.exe"
    shutil.copy2(dist_exe, target_exe)

    # 2. Copy Default settings.json
    settings_src = root_dir / "settings.json"
    if settings_src.exists():
        shutil.copy2(settings_src, package_dir / "settings.json")

    # 3. Create User Guide & Quick Start README.txt
    readme_content = """========================================================================
                 OFFICE TIME WIDGET - PORTABLE EDITION
========================================================================

NO PYTHON REQUIRED! This application is 100% self-contained and portable.

HOW TO RUN:
1. Extract this folder to any location on your PC (e.g. Desktop, Documents, or USB drive).
2. Double-click 'OfficeTimeWidget.exe' to launch.

KEY FEATURES:
- Automatic Clock-In: Starts recording work time as soon as launched.
- Large Digital Clock & Calendar Widget (frameless, draggable, snap-to-edge).
- Milestone Progress Bars:
  * Daily Minimum: 4.0 hours (✅ badge when reached)
  * Daily Target: 8.0 hours (Overtime tracker when exceeded)
  * Weekly Target: 36.0 hours (Monday to Sunday balance)
- Interactive Monthly Calendar & Day-by-Day session drawer.
- Styled Excel Timesheet Export (.xlsx).
- Windows System Tray integration with milestone balloon notifications.
- Windows Auto-Start option (available in Settings ⚙️).

PORTABILITY:
All work records are stored locally in 'time_tracker.db' inside this folder.
You can copy this folder to any Windows 10/11 computer and keep all your records!

========================================================================
"""
    with open(package_dir / "README.txt", "w", encoding="utf-8") as f:
        f.write(readme_content)

    # 4. Create ZIP archive
    zip_path = release_root / f"{package_folder_name}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(package_dir):
            for file in files:
                file_path = Path(root) / file
                archive_name = Path(package_folder_name) / file_path.relative_to(package_dir)
                zf.write(file_path, archive_name)

    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print("=" * 60)
    print("  [SUCCESS] Publishable Release Package Created!")
    print(f"  Folder: {package_dir}")
    print(f"  ZIP:    {zip_path} ({size_mb:.2f} MB)")
    print("=" * 60)
    return zip_path, package_dir


if __name__ == "__main__":
    create_publishable_release()
