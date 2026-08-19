"""
System Tray Manager for Office Time Widget.
Provides dynamic tray icon rendering, status tooltips, quick-actions context menu,
and milestone desktop notifications.
"""

from datetime import date, datetime
from typing import Callable, Optional

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QAction, QBrush, QColor, QFont, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QMenu, QMessageBox, QSystemTrayIcon

from config import config
from db import db


class TrayManager(QObject):
    """Manages the Windows System Tray icon, menu, and balloon notifications."""

    request_toggle_widget = Signal()
    request_open_reports = Signal()
    request_open_settings = Signal()
    request_clock_in = Signal()
    request_clock_out = Signal()
    request_start_break = Signal()
    request_end_break = Signal()
    request_export_excel = Signal()
    request_exit = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tray_icon = QSystemTrayIcon(parent)

        # Milestone notification flags
        self._notified_min_today = False
        self._notified_target_today = False
        self._notified_target_week = False
        self._last_tracked_day = date.today()

        self._init_menu()
        self.update_tray_state()
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _create_icon_pixmap(self, status: str = "idle") -> QIcon:
        """Draws a clean modern high-DPI tray icon with status accent dot."""
        size = 64
        pixmap = QPixmap(size, size)
        pixmap.fill(QColor(0, 0, 0, 0))

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Outer Clock Circle
        outer_pen = QPen(QColor("#38BDF8"), 4)
        painter.setPen(outer_pen)
        painter.setBrush(QBrush(QColor("#0F172A")))
        painter.drawEllipse(6, 6, 52, 52)

        # Clock Hands
        hand_pen = QPen(QColor("#FFFFFF"), 4)
        hand_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(hand_pen)
        painter.drawLine(32, 32, 32, 16)  # 12 o'clock hand
        painter.drawLine(32, 32, 44, 32)  # 3 o'clock hand

        # Center Pivot
        painter.setBrush(QBrush(QColor("#38BDF8")))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(29, 29, 6, 6)

        # Status Indicator Badge
        if status == "working":
            badge_color = QColor("#10B981")  # Emerald Green
        elif status == "break":
            badge_color = QColor("#F59E0B")  # Amber
        else:
            badge_color = QColor("#64748B")  # Slate Gray

        painter.setBrush(QBrush(badge_color))
        painter.setPen(QPen(QColor("#0F172A"), 3))
        painter.drawEllipse(42, 42, 18, 18)

        painter.end()
        return QIcon(pixmap)

    def _init_menu(self):
        self.menu = QMenu()

        # Status Info Header (Disabled)
        self.action_status_header = QAction("Office Time Tracker", self.menu)
        self.action_status_header.setEnabled(False)
        self.menu.addAction(self.action_status_header)
        self.menu.addSeparator()

        # Quick Action Controls
        self.action_clock_in = QAction("⚡ Clock In", self.menu)
        self.action_clock_in.triggered.connect(self.request_clock_in.emit)
        self.menu.addAction(self.action_clock_in)

        self.action_clock_out = QAction("⏹ Clock Out", self.menu)
        self.action_clock_out.triggered.connect(self.request_clock_out.emit)
        self.menu.addAction(self.action_clock_out)

        self.action_break = QAction("☕ Take Break", self.menu)
        self.action_break.triggered.connect(self.request_start_break.emit)
        self.menu.addAction(self.action_break)

        self.action_resume = QAction("▶ Resume Work", self.menu)
        self.action_resume.triggered.connect(self.request_end_break.emit)
        self.menu.addAction(self.action_resume)

        self.menu.addSeparator()

        # Window & Reports Controls
        self.action_toggle = QAction("👁️ Show / Hide Widget", self.menu)
        self.action_toggle.triggered.connect(self.request_toggle_widget.emit)
        self.menu.addAction(self.action_toggle)

        self.action_reports = QAction("📅 Monthly Calendar & Reports", self.menu)
        self.action_reports.triggered.connect(self.request_open_reports.emit)
        self.menu.addAction(self.action_reports)

        self.action_export = QAction("📥 Export Excel Report", self.menu)
        self.action_export.triggered.connect(self.request_export_excel.emit)
        self.menu.addAction(self.action_export)

        self.action_settings = QAction("⚙️ Settings", self.menu)
        self.action_settings.triggered.connect(self.request_open_settings.emit)
        self.menu.addAction(self.action_settings)

        self.menu.addSeparator()

        self.action_exit = QAction("❌ Exit", self.menu)
        self.action_exit.triggered.connect(self.request_exit.emit)
        self.menu.addAction(self.action_exit)

        self.tray_icon.setContextMenu(self.menu)

    def _on_tray_activated(self, reason):
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.request_toggle_widget.emit()

    def update_tray_state(self):
        """Updates tray icon glyph, tooltip, context menu enable states, and checks milestone triggers."""
        today = date.today()
        if today != self._last_tracked_day:
            # Reset daily milestone alerts on date change
            self._notified_min_today = False
            self._notified_target_today = False
            self._last_tracked_day = today

        day_sum = db.get_today_summary()
        week_sum = db.get_week_summary()
        status = day_sum["status"]

        # Update Icon
        self.tray_icon.setIcon(self._create_icon_pixmap(status))

        # Format Tooltip
        work_sec = day_sum["total_work_sec"]
        h = int(work_sec // 3600)
        m = int((work_sec % 3600) // 60)
        target_h = config.get("daily_target_hours", 8.0)
        week_work_h = week_sum["total_week_work_sec"] / 3600.0
        week_target_h = config.get("weekly_target_hours", 36.0)

        status_label = {
            "working": "Working",
            "break": "On Break",
            "idle": "Idle",
        }.get(status, "Idle")

        tooltip = (
            f"Office Time Tracker\n"
            f"Status: {status_label}\n"
            f"Today: {h}h {m:02d}m / {target_h:.1f}h ({int(day_sum['target_progress']*100)}%)\n"
            f"This Week: {week_work_h:.1f}h / {week_target_h:.1f}h"
        )
        self.tray_icon.setToolTip(tooltip)

        # Context Menu item states
        self.action_status_header.setText(f"● {status_label.upper()} — Today: {h}h {m:02d}m")
        if status == "working":
            self.action_clock_in.setVisible(False)
            self.action_clock_out.setVisible(True)
            self.action_break.setVisible(True)
            self.action_resume.setVisible(False)
        elif status == "break":
            self.action_clock_in.setVisible(False)
            self.action_clock_out.setVisible(True)
            self.action_break.setVisible(False)
            self.action_resume.setVisible(True)
        else:  # idle
            self.action_clock_in.setVisible(True)
            self.action_clock_out.setVisible(False)
            self.action_break.setVisible(False)
            self.action_resume.setVisible(False)

        # Check Milestone Notifications
        self._check_milestone_notifications(day_sum, week_sum)

    def _check_milestone_notifications(self, day_sum: dict, week_sum: dict):
        if not config.get("notifications_enabled", True):
            return

        # 1. Daily Minimum Reached (4h)
        if day_sum["min_reached"] and not self._notified_min_today:
            self._notified_min_today = True
            min_h = config.get("daily_min_hours", 4.0)
            self.show_notification(
                "Daily Minimum Reached! ✅",
                f"You have reached your daily minimum of {min_h:.1f} hours worked today.",
            )

        # 2. Daily Target Reached (8h)
        if day_sum["target_reached"] and not self._notified_target_today:
            self._notified_target_today = True
            target_h = config.get("daily_target_hours", 8.0)
            self.show_notification(
                "Daily Target Achieved! 🎉",
                f"Great job! You have completed your {target_h:.1f} hours target for today.",
            )

        # 3. Weekly Target Reached (36h)
        if week_sum["target_reached"] and not self._notified_target_week:
            self._notified_target_week = True
            w_target_h = config.get("weekly_target_hours", 36.0)
            self.show_notification(
                "Weekly Target Completed! 🏆",
                f"Awesome! You have hit your {w_target_h:.1f} hours weekly target!",
            )

    def show_notification(self, title: str, message: str):
        """Displays Windows balloon/toast notification via system tray."""
        self.tray_icon.showMessage(
            title,
            message,
            QSystemTrayIcon.MessageIcon.Information,
            5000,
        )
