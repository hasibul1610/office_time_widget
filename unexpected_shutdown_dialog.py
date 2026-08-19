"""
Unexpected Shutdown / Unclosed Session Recovery Dialog.
Pops up on application launch if a session from a prior day was left in 'working' or 'break' status.
"""

from datetime import datetime, timedelta
from typing import Dict, Optional

from PySide6.QtCore import QDate, QTime, Qt
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTimeEdit,
    QVBoxLayout,
)

from config import config
from db import db
from theme import get_theme_stylesheet


class UnexpectedShutdownDialog(QDialog):
    """Dialog allowing users to resolve unclosed sessions from previous days."""

    def __init__(self, session: Dict, parent=None):
        super().__init__(parent)
        self.session = session
        self.setWindowTitle("⚠️ Unexpected Shutdown Detected")
        self.resize(420, 460)
        self.setModal(True)
        self.setStyleSheet(get_theme_stylesheet(config.get("theme", "dark")))

        self._init_ui()
        self._load_session_details()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        # Warning Banner Card
        banner_card = QFrame()
        banner_card.setStyleSheet(
            "background-color: rgba(239, 68, 68, 0.15); border: 1px solid #EF4444; border-radius: 10px;"
        )
        banner_layout = QHBoxLayout(banner_card)
        banner_layout.setContentsMargins(12, 10, 12, 10)
        banner_layout.setSpacing(10)

        warn_icon = QLabel("⚠️")
        warn_icon.setStyleSheet("font-size: 24px;")

        warn_text = QLabel(
            "Unclosed Session Found!\nYour computer appears to have shut down unexpectedly without Clocking Out."
        )
        warn_text.setStyleSheet("color: #FCA5A5; font-weight: bold; font-size: 12px;")
        warn_text.setWordWrap(True)

        banner_layout.addWidget(warn_icon)
        banner_layout.addWidget(warn_text, 1)

        layout.addWidget(banner_card)

        # Form Card
        form_card = QFrame()
        form_card.setObjectName("CardFrame")
        form_layout = QFormLayout(form_card)
        form_layout.setSpacing(12)
        form_layout.setContentsMargins(14, 14, 14, 14)

        # Session Date (Read-only label)
        self.lbl_session_date = QLabel("2026-08-17")
        self.lbl_session_date.setStyleSheet("font-weight: bold; color: #38BDF8;")
        form_layout.addRow("Session Date:", self.lbl_session_date)

        # Clock In Time (Read-only label)
        self.lbl_clock_in = QLabel("09:00:00")
        self.lbl_clock_in.setStyleSheet("font-weight: bold; color: #F8FAFC;")
        form_layout.addRow("Clock In Time:", self.lbl_clock_in)

        # Specified Clock Out Time
        self.time_out_edit = QTimeEdit()
        self.time_out_edit.setDisplayFormat("HH:mm:ss")
        self.time_out_edit.timeChanged.connect(self._update_calculated_preview)
        form_layout.addRow("Actual Clock Out:", self.time_out_edit)

        # Break Duration
        self.break_spin = QSpinBox()
        self.break_spin.setRange(0, 720)
        self.break_spin.setValue(0)
        self.break_spin.setSuffix(" mins")
        self.break_spin.valueChanged.connect(self._update_calculated_preview)
        form_layout.addRow("Break Time:", self.break_spin)

        # Notes
        self.notes_edit = QLineEdit()
        self.notes_edit.setPlaceholderText("Notes (e.g. PC shutdown at 5:30 PM)...")
        form_layout.addRow("Notes:", self.notes_edit)

        layout.addWidget(form_card)

        # Net Duration Preview Box
        preview_card = QFrame()
        preview_card.setObjectName("HighlightCard")
        preview_layout = QHBoxLayout(preview_card)
        preview_layout.setContentsMargins(12, 10, 12, 10)

        preview_icon = QLabel("⏱️")
        self.preview_label = QLabel("Net Working Time: 8h 00m (8.00 hrs)")
        self.preview_label.setStyleSheet("font-weight: 600; font-size: 12px; color: #38BDF8;")
        preview_layout.addWidget(preview_icon)
        preview_layout.addWidget(self.preview_label)
        preview_layout.addStretch()

        layout.addWidget(preview_card)

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.btn_discard = QPushButton("🗑️ Discard Session")
        self.btn_discard.setStyleSheet("background-color: #7F1D1D; color: #FECACA; border-color: #991B1B;")
        self.btn_discard.clicked.connect(self._on_discard)

        self.btn_save = QPushButton("✅ Save & Fix Session")
        self.btn_save.setObjectName("PrimaryBtn")
        self.btn_save.clicked.connect(self._on_save)

        btn_layout.addWidget(self.btn_discard)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_save)

        layout.addLayout(btn_layout)

    def _load_session_details(self):
        s_date_str = self.session.get("session_date", "")
        self.lbl_session_date.setText(s_date_str)

        clock_in_str = self.session.get("clock_in", "")
        try:
            dt_in = datetime.fromisoformat(clock_in_str)
            self.lbl_clock_in.setText(dt_in.strftime("%H:%M:%S (%I:%M %p)"))

            # Default clock out: clock_in + daily_target_hours (e.g. 8 hours later)
            target_hours = float(config.get("daily_target_hours", 8.0))
            dt_out_suggested = dt_in + timedelta(hours=target_hours)
            self.time_out_edit.setTime(
                QTime(dt_out_suggested.hour, dt_out_suggested.minute, dt_out_suggested.second)
            )
        except Exception:
            self.lbl_clock_in.setText(clock_in_str)
            self.time_out_edit.setTime(QTime(17, 30, 0))

        b_mins = int(round(float(self.session.get("break_duration_seconds", 0.0) or 0.0) / 60.0))
        self.break_spin.setValue(b_mins)

        existing_notes = self.session.get("notes", "") or ""
        if existing_notes:
            self.notes_edit.setText(existing_notes)
        else:
            self.notes_edit.setText("Auto-fixed after unexpected PC shutdown")

        self._update_calculated_preview()

    def _update_calculated_preview(self):
        clock_in_str = self.session.get("clock_in", "")
        try:
            dt_in = datetime.fromisoformat(clock_in_str)
            t_in_sec = dt_in.hour * 3600 + dt_in.minute * 60 + dt_in.second
        except Exception:
            t_in_sec = 9 * 3600

        t_out = self.time_out_edit.time()
        t_out_sec = t_out.hour() * 3600 + t_out.minute() * 60 + t_out.second()

        total_elapsed = t_out_sec - t_in_sec
        if total_elapsed < 0:
            total_elapsed += 24 * 3600  # Crosses midnight

        break_sec = self.break_spin.value() * 60
        net_sec = max(0, total_elapsed - break_sec)
        net_hrs = net_sec / 3600.0

        h = net_sec // 3600
        m = (net_sec % 3600) // 60
        self.preview_label.setText(f"Net Working Time: {h}h {m:02d}m ({net_hrs:.2f} hrs)")

    def _on_discard(self):
        res = QMessageBox.question(
            self,
            "Discard Session",
            "Are you sure you want to discard and delete this unclosed session?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if res == QMessageBox.StandardButton.Yes:
            db.delete_session(self.session["id"])
            self.accept()

    def _on_save(self):
        s_id = self.session["id"]
        s_date_str = self.session["session_date"]
        clock_in_str = self.session["clock_in"]

        try:
            d = datetime.strptime(s_date_str, "%Y-%m-%d").date()
        except Exception:
            d = datetime.now().date()

        t_out = self.time_out_edit.time()
        clock_out_dt = datetime(d.year, d.month, d.day, t_out.hour(), t_out.minute(), t_out.second())

        dt_in = datetime.fromisoformat(clock_in_str)
        if clock_out_dt < dt_in:
            clock_out_dt += timedelta(days=1)

        break_seconds = self.break_spin.value() * 60.0
        notes = self.notes_edit.text().strip()

        db.update_session(
            session_id=s_id,
            session_date=s_date_str,
            clock_in=clock_in_str,
            clock_out=clock_out_dt.isoformat(timespec="seconds"),
            break_duration_seconds=break_seconds,
            notes=notes,
        )

        self.accept()
