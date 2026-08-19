"""
Configuration and settings manager for Office Time Widget.
Handles JSON persistence and Windows Registry auto-start integration.
"""

import json
import os
import sys
import winreg
from pathlib import Path
from typing import Any, Dict


def get_app_dir() -> Path:
    """Returns the portable application base directory."""
    if getattr(sys, "frozen", False):
        # Running as PyInstaller bundle
        return Path(sys.executable).parent.resolve()
    else:
        # Running from source
        return Path(__file__).parent.resolve()


def get_data_dir() -> Path:
    """
    Returns the directory for storing database and config.
    Prioritizes the portable app directory, falling back to APPDATA if not writable.
    """
    app_dir = get_app_dir()
    try:
        test_file = app_dir / ".write_test"
        test_file.touch()
        test_file.unlink()
        return app_dir
    except (PermissionError, OSError):
        appdata = Path(os.environ.get("APPDATA", str(Path.home()))) / "OfficeTimeWidget"
        appdata.mkdir(parents=True, exist_ok=True)
        return appdata


DEFAULT_SETTINGS: Dict[str, Any] = {
    "daily_min_hours": 4.0,
    "daily_target_hours": 8.0,
    "weekly_target_hours": 36.0,
    "always_on_top": True,
    "opacity": 0.96,
    "theme": "dark",  # 'dark', 'light'
    "clock_font_size": "large",  # 'standard' (50px), 'large' (64px), 'xlarge' (76px), 'jumbo' (88px)
    "auto_start": False,
    "auto_clock_in_on_startup": True,
    "auto_clock_out_on_shutdown": True,
    "work_days": [0, 1, 2, 3, 4, 5, 6],  # Mon through Sun enabled by default
    "notifications_enabled": True,
    "sound_alerts": True,
    "snap_to_edges": True,
    "clock_24h": False,  # 12-hour clock format by default
    "show_seconds": True,
    "minimize_to_tray_on_close": True,
    "widget_x": -1,
    "widget_y": -1,
    "collapsed": False,
}

REGISTRY_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_REG_NAME = "OfficeTimeWidget"


class ConfigManager:
    """Manages application settings and Windows Registry auto-start."""

    def __init__(self):
        self.data_dir = get_data_dir()
        self.config_path = self.data_dir / "settings.json"
        self.settings = DEFAULT_SETTINGS.copy()
        self.load()

    def load(self) -> Dict[str, Any]:
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.settings.update(data)
            except Exception as e:
                print(f"Warning: Failed to load config from {self.config_path}: {e}")
        else:
            self.save()
        return self.settings

    def save(self) -> None:
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            print(f"Error saving config to {self.config_path}: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        return self.settings.get(key, default)

    def set(self, key: str, value: Any, auto_save: bool = True) -> None:
        self.settings[key] = value
        if auto_save:
            self.save()

    def update(self, new_settings: Dict[str, Any]) -> None:
        self.settings.update(new_settings)
        self.save()

    # --- Windows Autostart Registry Management ---

    @staticmethod
    def get_executable_path() -> str:
        """Returns the appropriate command to launch at Windows startup."""
        if getattr(sys, "frozen", False):
            return f'"{sys.executable}"'
        else:
            python_exe = sys.executable
            # If pythonw exists, use it to avoid console popup
            pythonw = Path(python_exe).parent / "pythonw.exe"
            if pythonw.exists():
                python_exe = str(pythonw)
            main_script = (Path(__file__).parent / "main.py").resolve()
            return f'"{python_exe}" "{main_script}"'

    def is_autostart_enabled(self) -> bool:
        """Checks if the application is registered in Windows Startup."""
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, REGISTRY_RUN_KEY, 0, winreg.KEY_READ
            ) as key:
                winreg.QueryValueEx(key, APP_REG_NAME)
                return True
        except (FileNotFoundError, OSError):
            return False

    def set_autostart(self, enable: bool) -> bool:
        """Enables or disables auto-start via Windows Registry."""
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                REGISTRY_RUN_KEY,
                0,
                winreg.KEY_SET_VALUE | winreg.KEY_READ,
            ) as key:
                if enable:
                    exe_cmd = self.get_executable_path()
                    winreg.SetValueEx(
                        key, APP_REG_NAME, 0, winreg.REG_SZ, exe_cmd
                    )
                else:
                    try:
                        winreg.DeleteValue(key, APP_REG_NAME)
                    except FileNotFoundError:
                        pass
            self.set("auto_start", enable)
            return True
        except Exception as e:
            print(f"Failed to update auto-start registry key: {e}")
            return False


# Global singleton instance
config = ConfigManager()
