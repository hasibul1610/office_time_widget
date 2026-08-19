"""
GUI Smoke test to verify all PySide6 widgets, dialogs, tray, and interactions initialize without errors.
"""

import os
import sys
import unittest
from datetime import date
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from config import config
from db import db
from manual_entry_dialog import ManualEntryDialog
from report_window import ReportWindow
from settings_dialog import SettingsDialog
from tray_manager import TrayManager
from widget import OfficeTimeWidget


class TestGUISmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def test_widget_lifecycle(self):
        config.set("auto_clock_in_on_startup", False, auto_save=False)
        db.clear_all_data()

        # Create widget
        widget = OfficeTimeWidget()
        self.assertIsNotNone(widget)

        # Trigger tick
        widget._on_tick()

        # Test Punch in and out
        widget._toggle_punch()  # Clock in
        day_sum = db.get_today_summary()
        self.assertEqual(day_sum["status"], "working")

        widget._toggle_break()  # Start break
        day_sum_break = db.get_today_summary()
        self.assertEqual(day_sum_break["status"], "break")

        widget._toggle_break()  # Resume
        day_sum_resumed = db.get_today_summary()
        self.assertEqual(day_sum_resumed["status"], "working")

        widget._toggle_punch()  # Clock out
        day_sum_out = db.get_today_summary()
        self.assertEqual(day_sum_out["status"], "idle")

        widget.close()

    def test_dialogs_instantiation(self):
        # Test Report Window
        rep = ReportWindow()
        rep.refresh_data()
        rep.close()

        # Test Settings Dialog
        settings = SettingsDialog()
        settings.close()

        # Test Manual Entry Dialog
        manual = ManualEntryDialog(default_date=date.today())
        manual.close()

    def test_tray_manager(self):
        widget = OfficeTimeWidget()
        tray = TrayManager(widget)
        tray.update_tray_state()
        widget.close()


if __name__ == "__main__":
    unittest.main()
