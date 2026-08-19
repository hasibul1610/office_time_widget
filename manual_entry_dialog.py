"""
Manual work session entry and editing dialog.
"""

from datetime import date, datetime, time
from typing import Any, Dict, Optional

from PySide6.QtCore import QDate, QTime, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDateEdit,
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

from db import db
from theme import get_theme_stylesheet
from config import config


class ManualEntryDialog(QDialog):
    """Dialog for creating or editing time tracking sessions."""

    def __init__(
        self,
        parent=None,
        session_id: Optional[int] = None,
        default_date: Optional[date] = None,
    ):
        super().__init__(parent)
        self.session_id = session_id
        self.default_date = default_date or date.today()
        self.setWindowTitle("Edit Session" if session_id else "Add Work Session")
        self.resize(380, 420)
        self.setModal(True)
        self.setStyleSheet(get_theme_stylesheet(config.get("theme", "dark")))

        self._init_ui()
        if self.session_id:
            self._load_existing_session()
        else:
            self._set_defaults()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header Title
        title_label = QLabel("Work Session Details")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #38BDF8;")
        layout.addWidget(title_label)

        form_card = QFrame()
        form_card.setObjectName("CardFrame")
        form_layout = QFormLayout(form_card)
        form_layout.setSpacing(12)
        form_layout.setContentsMargins(14, 14, 14, 14)

        # Date Picker
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setDate(QDate(self.default_date.year, self.default_date.month, self.default_date.day))
        form_layout.addRow("Date:", self.date_edit)

        # Clock In Time
        self.time_in_edit = QTimeEdit()
        self.time_in_edit.setDisplayFormat("HH:mm:ss")
        self.time_in_edit.setTime(QTime(9, 0, 0))
        self.time_in_edit.timeChanged.connect(self._update_calculated_preview)
        form_layout.addRow("Clock In:", self.time_in_edit)

        # Clock Out Time
        self.time_out_edit = QTimeEdit()
        self.time_out_edit.setDisplayFormat("HH:mm:ss")
        self.time_out_edit.setTime(QTime(17, 30, 0))
        self.time_out_edit.timeChanged.connect(self._update_calculated_preview)
        form_layout.addRow("Clock Out:", self.time_out_edit)

        # Break Duration (Minutes)
        self.break_spin = QSpinBox()
        self.break_spin.setRange(0, 720)
        self.break_spin.setValue(30)
        self.break_spin.setSuffix(" mins")
        self.break_spin.valueChanged.connect(self._update_calculated_preview)
        form_layout.addRow("Break Time:", self.break_spin)

        # Notes
        self.notes_edit = QLineEdit()
        self.notes_edit.setPlaceholderText("Optional task or shift description...")
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

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)

        self.save_btn = QPushButton("Save Session")
        self.save_btn.setObjectName("PrimaryBtn")
        self.save_btn.clicked.connect(self._on_save)

        btn_layout.addStretch()
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.save_btn)

        layout.addLayout(btn_layout)

    def _set_defaults(self):
        self._update_calculated_preview()

    def _load_existing_session(self):
        s = db.get_session_by_id(self.session_id)
        if not s:
            QMessageBox.critical(self, "Error", "Session could not be found.")
            self.reject()
            return

        d = datetime.strptime(s["session_date"], "%Y-%m-%d").date()
        self.date_edit.setDate(QDate(d.year, d.month, d.day))

        dt_in = datetime.fromisoformat(s["clock_in"])
        self.time_in_edit.setTime(QTime(dt_in.hour, dt_in.minute, dt_in.second))

        if s.get("clock_out"):
            dt_out = datetime.fromisoformat(s["clock_out"])
            self.time_out_edit.setTime(QTime(dt_out.hour, dt_out.minute, dt_out.second))
        else:
            now = datetime.now()
            self.time_out_edit.setTime(QTime(now.hour, now.minute, now.second))

        b_mins = int(round(float(s.get("break_duration_seconds", 0.0) or 0.0) / 60.0))
        self.break_spin.setValue(b_mins)
        self.notes_edit.setText(s.get("notes", "") or "")

        self._update_calculated_preview()

    def _update_calculated_preview(self):
        t_in = self.time_in_edit.time()
        t_out = self.time_out_edit.time()
        b_mins = self.break_spin.value()

        sec_in = t_in.hour() * 3600 + t_in.minute() * 60 + t_in.second()
        sec_out = t_out.hour() * 3600 + t_out.minute() * 60 + t_out.second()

        total_elapsed = sec_out - sec_in
        if total_elapsed < 0:
            total_elapsed += 24 * 3600  # Crosses midnight

        break_sec = b_mins * 60
        net_sec = max(0, total_elapsed - break_sec)
        net_hrs = net_sec / 3600.0

        h = net_sec // 3600
        m = (net_sec % 3600) // 60
        self.preview_label.setText(f"Net Working Time: {h}h {m:02d}m ({net_hrs:.2f} hrs)")

    def _on_save(self):
        q_date = self.date_edit.date()
        date_str = f"{q_date.year():04d}-{q_date.month():02d}-{q_date.day():02d}"

        t_in = self.time_in_edit.time()
        t_out = self.time_out_edit.time()

        clock_in_dt = datetime(
            q_date.year(), q_date.month(), q_date.day(), t_in.hour(), t_in.minute(), t_in.second()
        )

        clock_out_dt = datetime(
            q_date.year(), q_date.month(), q_date.day(), t_out.hour(), t_out.minute(), t_out.second()
        )

        if clock_out_dt < clock_in_dt:
            # Shift spans midnight into next day
            from datetime import timedelta
            clock_out_dt += timedelta(days=1)

        break_seconds = self.break_spin.value() * 60.0
        notes = self.notes_edit.text().strip()

        if self.session_id:
            db.update_session(
                session_id=self.session_id,
                session_date=date_str,
                clock_in=clock_in_dt.isoformat(timespec="seconds"),
                clock_out=clock_out_dt.isoformat(timespec="seconds"),
                break_duration_seconds=break_seconds,
                notes=notes,
            )
        else:
            db.add_manual_session(
                session_date=date_str,
                clock_in=clock_in_dt.isoformat(timespec="seconds"),
                clock_out=clock_out_dt.isoformat(timespec="seconds"),
                break_duration_seconds=break_seconds,
                notes=notes,
            )

        self.accept()
