"""
Settings and preferences dialog for Office Time Widget.
"""

import os
import sys
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSlider,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from config import config, get_data_dir
from db import db
from theme import get_theme_stylesheet


class SettingsDialog(QDialog):
    """Configuration dialog for targets, appearance, autostart, and database maintenance."""

    settings_saved = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Office Time Tracker - Settings")
        self.resize(520, 560)
        self.setModal(True)
        self.setStyleSheet(
            get_theme_stylesheet(
                config.get("theme", "dark"),
                config.get("clock_font_size", "large"),
            )
        )

        self._init_ui()
        self._load_values()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(18, 18, 18, 18)

        # Header Title
        title_box = QHBoxLayout()
        icon_lbl = QLabel("⚙️")
        icon_lbl.setStyleSheet("font-size: 20px;")
        title_lbl = QLabel("Preferences & Configuration")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #38BDF8;")
        title_box.addWidget(icon_lbl)
        title_box.addWidget(title_lbl)
        title_box.addStretch()
        main_layout.addLayout(title_box)

        # Tabs
        self.tabs = QTabWidget()

        # Tab 1: Work Hours & Targets
        tab_targets = QWidget()
        targets_layout = QVBoxLayout(tab_targets)
        targets_layout.setSpacing(14)
        targets_layout.setContentsMargins(14, 14, 14, 14)

        card_targets = QFrame()
        card_targets.setObjectName("CardFrame")
        form_targets = QFormLayout(card_targets)
        form_targets.setSpacing(14)
        form_targets.setContentsMargins(14, 14, 14, 14)

        self.spin_daily_min = QDoubleSpinBox()
        self.spin_daily_min.setRange(0.5, 24.0)
        self.spin_daily_min.setSingleStep(0.5)
        self.spin_daily_min.setSuffix(" hrs")
        form_targets.addRow("Daily Minimum Target:", self.spin_daily_min)

        self.spin_daily_target = QDoubleSpinBox()
        self.spin_daily_target.setRange(1.0, 24.0)
        self.spin_daily_target.setSingleStep(0.5)
        self.spin_daily_target.setSuffix(" hrs")
        form_targets.addRow("Daily Standard Target:", self.spin_daily_target)

        self.spin_weekly_target = QDoubleSpinBox()
        self.spin_weekly_target.setRange(5.0, 168.0)
        self.spin_weekly_target.setSingleStep(1.0)
        self.spin_weekly_target.setSuffix(" hrs")
        form_targets.addRow("Weekly Standard Target:", self.spin_weekly_target)

        # Office Work Days
        days_layout = QHBoxLayout()
        days_layout.setSpacing(6)
        self.day_checkboxes = {}
        # Mon(0), Tue(1), Wed(2), Thu(3), Fri(4), Sat(5), Sun(6)
        days_info = [
            ("Mon", 0),
            ("Tue", 1),
            ("Wed", 2),
            ("Thu", 3),
            ("Fri", 4),
            ("Sat", 5),
            ("Sun", 6),
        ]
        for name, val in days_info:
            chk = QCheckBox(name)
            self.day_checkboxes[val] = chk
            days_layout.addWidget(chk)

        form_targets.addRow("Working Days:", days_layout)

        targets_layout.addWidget(card_targets)

        info_targets = QLabel(
            "ℹ️ Configured office targets drive daily/weekly summaries, dynamic Advice Ticker, and Excel reports."
        )
        info_targets.setStyleSheet("color: #94A3B8; font-size: 11px; font-style: italic;")
        info_targets.setWordWrap(True)
        targets_layout.addWidget(info_targets)
        targets_layout.addStretch()

        self.tabs.addTab(tab_targets, "🎯 Targets")

        # Tab 2: Appearance & Typography
        tab_app = QWidget()
        app_layout = QVBoxLayout(tab_app)
        app_layout.setSpacing(14)
        app_layout.setContentsMargins(14, 14, 14, 14)

        card_app = QFrame()
        card_app.setObjectName("CardFrame")
        form_app = QFormLayout(card_app)
        form_app.setSpacing(12)
        form_app.setContentsMargins(14, 14, 14, 14)

        self.combo_theme = QComboBox()
        self.combo_theme.addItems(["Dark Glass (Default)", "Light Clean"])
        form_app.addRow("Theme:", self.combo_theme)

        # Clock Font Size
        self.combo_clock_size = QComboBox()
        self.combo_clock_size.addItem("Standard (50px)", "standard")
        self.combo_clock_size.addItem("Large (64px) [Default]", "large")
        self.combo_clock_size.addItem("Extra Large (76px)", "xlarge")
        self.combo_clock_size.addItem("Jumbo (88px)", "jumbo")
        form_app.addRow("Clock Font Size:", self.combo_clock_size)

        # Opacity Slider
        opacity_row = QHBoxLayout()
        self.slider_opacity = QSlider(Qt.Orientation.Horizontal)
        self.slider_opacity.setRange(50, 100)
        self.slider_opacity.setValue(96)
        self.lbl_opacity_val = QLabel("96%")
        self.slider_opacity.valueChanged.connect(
            lambda v: self.lbl_opacity_val.setText(f"{v}%")
        )
        opacity_row.addWidget(self.slider_opacity)
        opacity_row.addWidget(self.lbl_opacity_val)
        form_app.addRow("Widget Opacity:", opacity_row)

        self.chk_always_on_top = QCheckBox("Always stay on top of other windows")
        form_app.addRow(self.chk_always_on_top)

        self.chk_24h = QCheckBox("Use 24-hour clock format (e.g. 15:30 vs 03:30 PM)")
        form_app.addRow(self.chk_24h)

        self.chk_show_seconds = QCheckBox("Display seconds on main clock")
        form_app.addRow(self.chk_show_seconds)

        self.chk_snap = QCheckBox("Snap widget to screen edges when dragging")
        form_app.addRow(self.chk_snap)

        app_layout.addWidget(card_app)
        app_layout.addStretch()
        self.tabs.addTab(tab_app, "🎨 Appearance")

        # Tab 3: Automation, System & Notifications
        tab_sys = QWidget()
        sys_layout = QVBoxLayout(tab_sys)
        sys_layout.setSpacing(14)
        sys_layout.setContentsMargins(14, 14, 14, 14)

        card_sys = QFrame()
        card_sys.setObjectName("CardFrame")
        form_sys = QFormLayout(card_sys)
        form_sys.setSpacing(12)
        form_sys.setContentsMargins(14, 14, 14, 14)

        self.chk_autostart = QCheckBox("Auto-start with Windows (Run automatically at login)")
        form_sys.addRow(self.chk_autostart)

        self.chk_auto_clock_in = QCheckBox("⚡ Auto Clock-In on startup / app launch (Start tracking immediately)")
        self.chk_auto_clock_in.setStyleSheet("font-weight: bold; color: #38BDF8;")
        form_sys.addRow(self.chk_auto_clock_in)

        self.chk_auto_clock_out = QCheckBox("⏹ Auto Clock-Out on shutdown / exit")
        form_sys.addRow(self.chk_auto_clock_out)

        self.chk_min_tray = QCheckBox("Minimize to System Tray when closing widget")
        form_sys.addRow(self.chk_min_tray)

        self.chk_notifications = QCheckBox("Show Milestone Desktop Notifications (4h, 8h, 36h)")
        form_sys.addRow(self.chk_notifications)

        self.chk_sound = QCheckBox("Play notification sound alerts")
        form_sys.addRow(self.chk_sound)

        sys_layout.addWidget(card_sys)
        sys_layout.addStretch()
        self.tabs.addTab(tab_sys, "💻 Automation & Tray")

        # Tab 4: Data & Maintenance
        tab_data = QWidget()
        data_layout = QVBoxLayout(tab_data)
        data_layout.setSpacing(14)
        data_layout.setContentsMargins(14, 14, 14, 14)

        card_data = QFrame()
        card_data.setObjectName("CardFrame")
        layout_data_card = QVBoxLayout(card_data)
        layout_data_card.setSpacing(10)
        layout_data_card.setContentsMargins(14, 14, 14, 14)

        btn_backup = QPushButton("💾 Backup SQLite Database")
        btn_backup.clicked.connect(self._on_backup_db)
        layout_data_card.addWidget(btn_backup)

        btn_open_folder = QPushButton("📁 Open App Data Directory")
        btn_open_folder.clicked.connect(self._on_open_data_folder)
        layout_data_card.addWidget(btn_open_folder)

        btn_clear_data = QPushButton("🗑️ Clear All Work Data")
        btn_clear_data.setStyleSheet("background-color: #7F1D1D; color: #FECACA; border-color: #991B1B;")
        btn_clear_data.clicked.connect(self._on_clear_data)
        layout_data_card.addWidget(btn_clear_data)

        data_layout.addWidget(card_data)
        data_layout.addStretch()
        self.tabs.addTab(tab_data, "🗄️ Database")

        main_layout.addWidget(self.tabs)

        # Dialog Footer Buttons
        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_save = QPushButton("Save Changes")
        self.btn_save.setObjectName("PrimaryBtn")
        self.btn_save.clicked.connect(self._on_save)

        btn_box.addStretch()
        btn_box.addWidget(self.btn_cancel)
        btn_box.addWidget(self.btn_save)

        main_layout.addLayout(btn_box)

    def _load_values(self):
        self.spin_daily_min.setValue(float(config.get("daily_min_hours", 4.0)))
        self.spin_daily_target.setValue(float(config.get("daily_target_hours", 8.0)))
        self.spin_weekly_target.setValue(float(config.get("weekly_target_hours", 36.0)))

        work_days = config.get("work_days", [0, 1, 2, 3, 4, 5, 6])
        for val, chk in self.day_checkboxes.items():
            chk.setChecked(val in work_days)

        theme = config.get("theme", "dark")
        self.combo_theme.setCurrentIndex(1 if theme == "light" else 0)

        clock_size = config.get("clock_font_size", "large")
        idx = self.combo_clock_size.findData(clock_size)
        if idx >= 0:
            self.combo_clock_size.setCurrentIndex(idx)
        else:
            self.combo_clock_size.setCurrentIndex(1)  # large default

        opacity = int(round(float(config.get("opacity", 0.96)) * 100))
        self.slider_opacity.setValue(opacity)
        self.lbl_opacity_val.setText(f"{opacity}%")

        self.chk_always_on_top.setChecked(bool(config.get("always_on_top", True)))
        self.chk_24h.setChecked(bool(config.get("clock_24h", False)))
        self.chk_show_seconds.setChecked(bool(config.get("show_seconds", True)))
        self.chk_snap.setChecked(bool(config.get("snap_to_edges", True)))

        # Check autostart from registry
        is_auto = config.is_autostart_enabled()
        self.chk_autostart.setChecked(is_auto)

        self.chk_auto_clock_in.setChecked(bool(config.get("auto_clock_in_on_startup", True)))
        self.chk_auto_clock_out.setChecked(bool(config.get("auto_clock_out_on_shutdown", True)))

        self.chk_min_tray.setChecked(bool(config.get("minimize_to_tray_on_close", True)))
        self.chk_notifications.setChecked(bool(config.get("notifications_enabled", True)))
        self.chk_sound.setChecked(bool(config.get("sound_alerts", True)))

    def _on_save(self):
        new_theme = "light" if self.combo_theme.currentIndex() == 1 else "dark"
        selected_work_days = [val for val, chk in self.day_checkboxes.items() if chk.isChecked()]
        clock_size = self.combo_clock_size.currentData() or "large"

        config.set("daily_min_hours", self.spin_daily_min.value(), auto_save=False)
        config.set("daily_target_hours", self.spin_daily_target.value(), auto_save=False)
        config.set("weekly_target_hours", self.spin_weekly_target.value(), auto_save=False)
        config.set("work_days", selected_work_days, auto_save=False)
        config.set("theme", new_theme, auto_save=False)
        config.set("clock_font_size", clock_size, auto_save=False)
        config.set("opacity", self.slider_opacity.value() / 100.0, auto_save=False)
        config.set("always_on_top", self.chk_always_on_top.isChecked(), auto_save=False)
        config.set("clock_24h", self.chk_24h.isChecked(), auto_save=False)
        config.set("show_seconds", self.chk_show_seconds.isChecked(), auto_save=False)
        config.set("snap_to_edges", self.chk_snap.isChecked(), auto_save=False)
        config.set("auto_clock_in_on_startup", self.chk_auto_clock_in.isChecked(), auto_save=False)
        config.set("auto_clock_out_on_shutdown", self.chk_auto_clock_out.isChecked(), auto_save=False)
        config.set("minimize_to_tray_on_close", self.chk_min_tray.isChecked(), auto_save=False)
        config.set("notifications_enabled", self.chk_notifications.isChecked(), auto_save=False)
        config.set("sound_alerts", self.chk_sound.isChecked(), auto_save=False)

        # Autostart Windows Registry Sync
        enable_auto = self.chk_autostart.isChecked()
        config.set_autostart(enable_auto)

        config.save()
        self.settings_saved.emit()
        self.accept()

    def _on_backup_db(self):
        data_dir = get_data_dir()
        backup_dir = data_dir / "backups"
        try:
            backup_path = db.backup_db(backup_dir)
            QMessageBox.information(
                self, "Backup Successful", f"Database backed up successfully to:\n{backup_path}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Backup Failed", f"Failed to backup database:\n{e}")

    def _on_open_data_folder(self):
        data_dir = get_data_dir()
        os.startfile(str(data_dir))

    def _on_clear_data(self):
        res = QMessageBox.warning(
            self,
            "Confirm Data Reset",
            "Are you sure you want to delete ALL logged work sessions and break records?\nThis cannot be undone!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if res == QMessageBox.StandardButton.Yes:
            db.clear_all_data()
            QMessageBox.information(self, "Cleared", "All time tracking records have been cleared.")
            self.settings_saved.emit()
