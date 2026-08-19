"""
Main Desktop Frameless Clock & Office Time Tracker Widget.
"""

import sys
from datetime import date, datetime
from typing import Optional

from PySide6.QtCore import QPoint, QRect, Qt, QTime, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QGuiApplication, QIcon, QMouseEvent
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from config import config
from db import db
from manual_entry_dialog import ManualEntryDialog
from report_window import ReportWindow
from settings_dialog import SettingsDialog
from theme import get_theme_stylesheet


class OfficeTimeWidget(QWidget):
    """Modern frameless, draggable desktop time tracker widget."""

    state_changed = Signal()

    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._setup_window_flags()

        # Dragging state
        self._dragging = False
        self._drag_start_pos = QPoint()
        self._current_tracked_day = date.today()

        # Child windows
        self.report_window: Optional[ReportWindow] = None
        self.settings_dialog: Optional[SettingsDialog] = None

        # Build UI
        self._init_ui()
        self._apply_theme()
        self._restore_position()

        # Check for startup auto clock-in immediately
        self._check_auto_clock_in()

        # 1-second update timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._on_tick)
        self.timer.start(1000)

        # Initial refresh
        self._update_display()

    def _setup_window_flags(self):
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.SubWindow
        if config.get("always_on_top", True):
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)

    def _init_ui(self):
        self.setFixedWidth(400)

        # Outer root layout for shadow margins
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(10, 10, 10, 10)

        # Main background container frame
        self.main_frame = QFrame(self)
        self.main_frame.setObjectName("MainWidget")

        # Soft drop shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 6)
        self.main_frame.setGraphicsEffect(shadow)

        self.card_layout = QVBoxLayout(self.main_frame)
        self.card_layout.setContentsMargins(16, 14, 16, 16)
        self.card_layout.setSpacing(12)

        # ----------------------------------------------------
        # 1. TOP HEADER TOOLBAR
        # ----------------------------------------------------
        header_layout = QHBoxLayout()
        header_layout.setSpacing(6)
        header_layout.setContentsMargins(0, 0, 0, 0)

        # App Icon & Title
        title_lbl = QLabel("⏱️ TIME TRACKER")
        title_lbl.setStyleSheet("font-size: 11px; font-weight: 800; color: #38BDF8; letter-spacing: 0.5px;")

        # Status Pill Badge
        self.status_badge = QLabel("IDLE")
        self.status_badge.setObjectName("StatusBadgeIdle")
        self.status_badge.setStyleSheet(
            "background-color: #334155; color: #94A3B8; border-radius: 8px; padding: 3px 10px; font-size: 11px; font-weight: bold;"
        )

        header_layout.addWidget(title_lbl)
        header_layout.addWidget(self.status_badge)
        header_layout.addStretch()

        # Pin (Always On Top) Button
        self.btn_pin = QPushButton("📌")
        self.btn_pin.setObjectName("IconButton")
        self.btn_pin.setToolTip("Toggle Always on Top")
        self.btn_pin.clicked.connect(self._toggle_always_on_top)
        header_layout.addWidget(self.btn_pin)

        # Collapse Button
        self.btn_collapse = QPushButton("🔼")
        self.btn_collapse.setObjectName("IconButton")
        self.btn_collapse.setToolTip("Compact / Expand View")
        self.btn_collapse.clicked.connect(self._toggle_collapse)
        header_layout.addWidget(self.btn_collapse)

        # Reports Button
        self.btn_reports = QPushButton("📅")
        self.btn_reports.setObjectName("IconButton")
        self.btn_reports.setToolTip("Monthly Calendar & Reports")
        self.btn_reports.clicked.connect(self.open_reports)
        header_layout.addWidget(self.btn_reports)

        # Settings Button
        self.btn_settings = QPushButton("⚙️")
        self.btn_settings.setObjectName("IconButton")
        self.btn_settings.setToolTip("Settings")
        self.btn_settings.clicked.connect(self.open_settings)
        header_layout.addWidget(self.btn_settings)

        # Minimize to Tray Button
        self.btn_min = QPushButton("🗕")
        self.btn_min.setObjectName("IconButton")
        self.btn_min.setToolTip("Minimize to System Tray")
        self.btn_min.clicked.connect(self.hide)
        header_layout.addWidget(self.btn_min)

        # Close Button
        self.btn_close = QPushButton("✕")
        self.btn_close.setObjectName("IconButton")
        self.btn_close.setToolTip("Close")
        self.btn_close.clicked.connect(self._on_close_clicked)
        header_layout.addWidget(self.btn_close)

        self.card_layout.addLayout(header_layout)

        # ----------------------------------------------------
        # 2. LARGE DIGITAL CLOCK & DATE BANNER
        # ----------------------------------------------------
        clock_card = QFrame()
        clock_card.setObjectName("CardFrame")
        clock_layout = QVBoxLayout(clock_card)
        clock_layout.setContentsMargins(14, 12, 14, 12)
        clock_layout.setSpacing(4)

        # Time row: Big Clock + Seconds
        time_row = QHBoxLayout()
        time_row.setSpacing(6)
        time_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_clock = QLabel("00:00")
        self.lbl_clock.setObjectName("ClockLabel")
        self.lbl_clock.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.lbl_seconds = QLabel(":00")
        self.lbl_seconds.setObjectName("SecondsLabel")
        self.lbl_seconds.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        time_row.addWidget(self.lbl_clock)
        time_row.addWidget(self.lbl_seconds)
        clock_layout.addLayout(time_row)

        # Date Label
        self.lbl_date = QLabel("Monday, 18 August 2026")
        self.lbl_date.setObjectName("DateLabel")
        self.lbl_date.setAlignment(Qt.AlignmentFlag.AlignCenter)
        clock_layout.addWidget(self.lbl_date)

        self.card_layout.addWidget(clock_card)

        # ----------------------------------------------------
        # 3. EXPANDABLE BODY (COLLAPSIBLE)
        # ----------------------------------------------------
        self.body_widget = QWidget()
        self.body_layout = QVBoxLayout(self.body_widget)
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(12)

        # Session Controls & Live Timers
        session_card = QFrame()
        session_card.setObjectName("CardFrame")
        session_card_layout = QVBoxLayout(session_card)
        session_card_layout.setContentsMargins(14, 14, 14, 14)
        session_card_layout.setSpacing(12)

        # Action Buttons Row
        action_btn_row = QHBoxLayout()
        action_btn_row.setSpacing(10)

        self.btn_punch = QPushButton("⚡ CLOCK IN")
        self.btn_punch.setObjectName("PrimaryBtn")
        self.btn_punch.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.btn_punch.clicked.connect(self._toggle_punch)

        self.btn_break = QPushButton("☕ BREAK")
        self.btn_break.setObjectName("BreakBtn")
        self.btn_break.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.btn_break.clicked.connect(self._toggle_break)
        self.btn_break.setEnabled(False)

        action_btn_row.addWidget(self.btn_punch)
        action_btn_row.addWidget(self.btn_break)
        session_card_layout.addLayout(action_btn_row)

        # Live Stopwatch Info Row
        timer_info_row = QHBoxLayout()
        timer_info_row.setContentsMargins(4, 0, 4, 0)

        # Session Timer
        session_time_box = QVBoxLayout()
        session_time_box.setSpacing(2)
        lbl_s_title = QLabel("CURRENT SESSION")
        lbl_s_title.setStyleSheet("font-size: 10px; font-weight: bold; color: #64748B;")
        self.lbl_session_time = QLabel("00h 00m 00s")
        self.lbl_session_time.setStyleSheet("font-size: 15px; font-weight: 800; color: #F8FAFC;")
        session_time_box.addWidget(lbl_s_title)
        session_time_box.addWidget(self.lbl_session_time)

        # Break Timer
        break_time_box = QVBoxLayout()
        break_time_box.setSpacing(2)
        lbl_b_title = QLabel("TODAY BREAK")
        lbl_b_title.setStyleSheet("font-size: 10px; font-weight: bold; color: #64748B;")
        self.lbl_break_time = QLabel("00m 00s")
        self.lbl_break_time.setStyleSheet("font-size: 15px; font-weight: 800; color: #F59E0B;")
        break_time_box.addWidget(lbl_b_title)
        break_time_box.addWidget(self.lbl_break_time)

        timer_info_row.addLayout(session_time_box)
        timer_info_row.addStretch()
        timer_info_row.addLayout(break_time_box)

        session_card_layout.addLayout(timer_info_row)
        self.body_layout.addWidget(session_card)

        # ----------------------------------------------------
        # 4. MILESTONE PROGRESS BARS (4h Min, 8h Target, 36h Week)
        # ----------------------------------------------------
        progress_card = QFrame()
        progress_card.setObjectName("CardFrame")
        progress_layout = QVBoxLayout(progress_card)
        progress_layout.setContentsMargins(14, 14, 14, 14)
        progress_layout.setSpacing(10)

        # Progress 1: Daily Minimum (4.0h)
        self.bar_min, self.lbl_min_text = self._create_progress_row(
            progress_layout, "DAILY MINIMUM (4h)", "MinBar"
        )

        # Progress 2: Daily Target (8.0h)
        self.bar_target, self.lbl_target_text = self._create_progress_row(
            progress_layout, "DAILY TARGET (8h)", "TargetBar"
        )

        # Progress 3: Weekly Target (36.0h)
        self.bar_week, self.lbl_week_text = self._create_progress_row(
            progress_layout, "WEEKLY TARGET (36h)", "WeekBar"
        )

        self.body_layout.addWidget(progress_card)

        # ----------------------------------------------------
        # 5. DYNAMIC STATUS & ADVICE TICKER
        # ----------------------------------------------------
        self.ticker_frame = QFrame()
        self.ticker_frame.setObjectName("HighlightCard")
        ticker_layout = QHBoxLayout(self.ticker_frame)
        ticker_layout.setContentsMargins(12, 10, 12, 10)
        ticker_layout.setSpacing(8)

        self.lbl_ticker_icon = QLabel("💡")
        self.lbl_ticker_icon.setStyleSheet("font-size: 15px;")
        self.lbl_ticker_msg = QLabel("Tracking active. Automatic recording enabled.")
        self.lbl_ticker_msg.setStyleSheet("font-size: 12px; font-weight: 600; color: #38BDF8;")
        self.lbl_ticker_msg.setWordWrap(True)

        ticker_layout.addWidget(self.lbl_ticker_icon)
        ticker_layout.addWidget(self.lbl_ticker_msg, 1)

        self.body_layout.addWidget(self.ticker_frame)

        # ----------------------------------------------------
        # 6. BOTTOM ACTION FOOTER
        # ----------------------------------------------------
        footer_layout = QHBoxLayout()
        footer_layout.setSpacing(10)

        btn_add_manual = QPushButton("➕ Add Time")
        btn_add_manual.clicked.connect(self._on_add_manual_time)

        btn_open_report = QPushButton("📊 Reports")
        btn_open_report.clicked.connect(self.open_reports)

        footer_layout.addWidget(btn_add_manual)
        footer_layout.addWidget(btn_open_report)

        self.body_layout.addLayout(footer_layout)

        self.card_layout.addWidget(self.body_widget)
        root_layout.addWidget(self.main_frame)

        if config.get("collapsed", False):
            self.body_widget.hide()
            self.btn_collapse.setText("🔽")

    def _create_progress_row(self, parent_layout: QVBoxLayout, label_text: str, bar_obj_name: str):
        row_header = QHBoxLayout()
        lbl_title = QLabel(label_text)
        lbl_title.setObjectName("SectionTitle")
        lbl_title.setStyleSheet("font-size: 11px; font-weight: bold; color: #94A3B8;")

        lbl_val = QLabel("0h 00m (0%)")
        lbl_val.setStyleSheet("font-size: 11px; font-weight: 700; color: #F8FAFC;")

        row_header.addWidget(lbl_title)
        row_header.addStretch()
        row_header.addWidget(lbl_val)
        parent_layout.addLayout(row_header)

        pbar = QProgressBar()
        pbar.setObjectName(bar_obj_name)
        pbar.setRange(0, 100)
        pbar.setValue(0)
        parent_layout.addWidget(pbar)

        return pbar, lbl_val

    def _apply_theme(self):
        theme_name = config.get("theme", "dark")
        clock_size = config.get("clock_font_size", "large")
        self.setStyleSheet(get_theme_stylesheet(theme_name, clock_size))
        opacity = float(config.get("opacity", 0.96))
        self.setWindowOpacity(opacity)

    def _check_auto_clock_in(self):
        """Auto clocks in immediately if auto_clock_in is enabled and there is no active session."""
        if not config.get("auto_clock_in_on_startup", True):
            return

        work_days = config.get("work_days", [0, 1, 2, 3, 4, 5, 6])
        today = date.today()
        if today.weekday() in work_days:
            active = db.get_active_session()
            if not active:
                db.clock_in("Auto Clock-In on startup")
                self._update_display()
                self.state_changed.emit()

    def _on_tick(self):
        """Called every second to update digital clock, live stopwatch, and progress bars."""
        today = date.today()
        if today != self._current_tracked_day:
            self._current_tracked_day = today
            # Auto-clock in on day turnover if enabled
            self._check_auto_clock_in()

        self._update_display()

    def _update_display(self):
        now = datetime.now()

        # 1. Update Digital Clock & Date
        is_24h = config.get("clock_24h", False)
        show_sec = config.get("show_seconds", True)

        if is_24h:
            time_str = now.strftime("%H:%M")
            self.lbl_clock.setText(time_str)
            if show_sec:
                self.lbl_seconds.setText(f":{now.strftime('%S')}")
                self.lbl_seconds.show()
            else:
                self.lbl_seconds.hide()
        else:
            time_str = now.strftime("%I:%M").lstrip("0")
            am_pm = now.strftime("%p")
            self.lbl_clock.setText(time_str)
            if show_sec:
                self.lbl_seconds.setText(f":{now.strftime('%S')} {am_pm}")
                self.lbl_seconds.show()
            else:
                self.lbl_seconds.setText(f" {am_pm}")
                self.lbl_seconds.show()

        self.lbl_date.setText(now.strftime("%A, %d %B %Y"))

        # 2. Get Live Summaries from Database
        day_sum = db.get_today_summary()
        week_sum = db.get_week_summary()

        status = day_sum["status"]
        total_work_sec = day_sum["total_work_sec"]
        total_break_sec = day_sum["total_break_sec"]
        curr_work_sec = day_sum["current_session_work_sec"]
        curr_break_sec = day_sum["current_break_sec"]

        # Format timers
        sw_h = int(curr_work_sec // 3600)
        sw_m = int((curr_work_sec % 3600) // 60)
        sw_s = int(curr_work_sec % 60)
        self.lbl_session_time.setText(f"{sw_h:02d}h {sw_m:02d}m {sw_s:02d}s")

        b_h = int(total_break_sec // 3600)
        b_m = int((total_break_sec % 3600) // 60)
        b_s = int(total_break_sec % 60)
        if b_h > 0:
            self.lbl_break_time.setText(f"{b_h}h {b_m:02d}m {b_s:02d}s")
        else:
            self.lbl_break_time.setText(f"{b_m:02d}m {b_s:02d}s")

        # 3. Update Status Badges & Action Buttons
        if status == "working":
            self.status_badge.setText("● WORKING")
            self.status_badge.setStyleSheet(
                "background-color: #065F46; color: #34D399; border-radius: 8px; padding: 3px 10px; font-size: 11px; font-weight: bold;"
            )
            self.btn_punch.setText("⏹ CLOCK OUT")
            self.btn_punch.setObjectName("StopBtn")
            self.btn_break.setText("☕ BREAK")
            self.btn_break.setObjectName("BreakBtn")
            self.btn_break.setEnabled(True)
        elif status == "break":
            self.status_badge.setText("● ON BREAK")
            self.status_badge.setStyleSheet(
                "background-color: #78350F; color: #FBBF24; border-radius: 8px; padding: 3px 10px; font-size: 11px; font-weight: bold;"
            )
            self.btn_punch.setText("⏹ CLOCK OUT")
            self.btn_punch.setObjectName("StopBtn")
            self.btn_break.setText("▶ RESUME")
            self.btn_break.setObjectName("ResumeBtn")
            self.btn_break.setEnabled(True)
        else:
            self.status_badge.setText("IDLE")
            self.status_badge.setStyleSheet(
                "background-color: #334155; color: #94A3B8; border-radius: 8px; padding: 3px 10px; font-size: 11px; font-weight: bold;"
            )
            self.btn_punch.setText("⚡ CLOCK IN")
            self.btn_punch.setObjectName("PrimaryBtn")
            self.btn_break.setText("☕ BREAK")
            self.btn_break.setObjectName("BreakBtn")
            self.btn_break.setEnabled(False)

        # Force re-styling of buttons
        self.btn_punch.style().unpolish(self.btn_punch)
        self.btn_punch.style().polish(self.btn_punch)
        self.btn_break.style().unpolish(self.btn_break)
        self.btn_break.style().polish(self.btn_break)

        # 4. Progress Bars Calculations
        min_sec = day_sum["min_sec"]
        target_sec = day_sum["target_sec"]
        week_target_sec = week_sum["weekly_target_sec"]

        # Daily Minimum (4h)
        min_pct = int(round(day_sum["min_progress"] * 100))
        self.bar_min.setValue(min_pct)
        min_h = int(total_work_sec // 3600)
        min_m = int((total_work_sec % 3600) // 60)
        if day_sum["min_reached"]:
            self.lbl_min_text.setText(f"{min_h}h {min_m:02d}m  ✅ Reached")
            self.lbl_min_text.setStyleSheet("color: #34D399; font-weight: bold; font-size: 11px;")
        else:
            self.lbl_min_text.setText(f"{min_h}h {min_m:02d}m / {min_sec/3600:.1f}h ({min_pct}%)")
            self.lbl_min_text.setStyleSheet("color: #F8FAFC; font-weight: 700; font-size: 11px;")

        # Daily Target (8h)
        target_pct = int(round(day_sum["target_progress"] * 100))
        self.bar_target.setValue(target_pct)
        if day_sum["target_reached"]:
            ot_h = int(day_sum["overtime_sec"] // 3600)
            ot_m = int((day_sum["overtime_sec"] % 3600) // 60)
            self.lbl_target_text.setText(f"🎉 Target Met! (+{ot_h}h {ot_m:02d}m)")
            self.lbl_target_text.setStyleSheet("color: #34D399; font-weight: bold; font-size: 11px;")
        else:
            self.lbl_target_text.setText(f"{min_h}h {min_m:02d}m / {target_sec/3600:.1f}h ({target_pct}%)")
            self.lbl_target_text.setStyleSheet("color: #F8FAFC; font-weight: 700; font-size: 11px;")

        # Weekly Target (36h)
        week_work_sec = week_sum["total_week_work_sec"]
        week_pct = int(round(week_sum["week_progress"] * 100))
        self.bar_week.setValue(week_pct)
        w_h = int(week_work_sec // 3600)
        w_m = int((week_work_sec % 3600) // 60)
        if week_sum["target_reached"]:
            self.lbl_week_text.setText(f"🏆 36h Met! ({w_h}h {w_m:02d}m)")
            self.lbl_week_text.setStyleSheet("color: #A78BFA; font-weight: bold; font-size: 11px;")
        else:
            self.lbl_week_text.setText(f"{w_h}h {w_m:02d}m / {week_target_sec/3600:.0f}h ({week_pct}%)")
            self.lbl_week_text.setStyleSheet("color: #F8FAFC; font-weight: 700; font-size: 11px;")

        # 5. Smart Dynamic Advice Ticker
        if status == "break":
            cb_m = int(curr_break_sec // 60)
            cb_s = int(curr_break_sec % 60)
            self.lbl_ticker_icon.setText("☕")
            self.lbl_ticker_msg.setText(f"On break for {cb_m}m {cb_s:02d}s. Take your time to recharge!")
        elif status == "working":
            self.lbl_ticker_icon.setText("⚡")
            if not day_sum["min_reached"]:
                rem_m = int(round(day_sum["remaining_to_min_sec"] / 60))
                self.lbl_ticker_msg.setText(
                    f"{rem_m//60}h {rem_m%60:02d}m left to reach your daily 4h minimum."
                )
            elif not day_sum["target_reached"]:
                rem_m = int(round(day_sum["remaining_to_target_sec"] / 60))
                self.lbl_ticker_msg.setText(
                    f"{rem_m//60}h {rem_m%60:02d}m left to reach your 8h daily target."
                )
            else:
                ot_m = int(round(day_sum["overtime_sec"] / 60))
                self.lbl_ticker_msg.setText(
                    f"Target completed! You are in overtime (+{ot_m//60}h {ot_m%60:02d}m)."
                )
        else:
            self.lbl_ticker_icon.setText("💡")
            self.lbl_ticker_msg.setText("Ready to work. Click Clock In or Auto Clock-In will start.")

    # --- Session Punching ---

    def _toggle_punch(self):
        active = db.get_active_session()
        if active:
            db.clock_out()
        else:
            db.clock_in()
        self._update_display()
        self.state_changed.emit()

    def _toggle_break(self):
        active = db.get_active_session()
        if not active:
            return
        if active["status"] == "break":
            db.end_break()
        else:
            db.start_break()
        self._update_display()
        self.state_changed.emit()

    def _on_add_manual_time(self):
        dlg = ManualEntryDialog(self)
        if dlg.exec() == ManualEntryDialog.DialogCode.Accepted:
            self._update_display()
            self.state_changed.emit()
            if self.report_window and self.report_window.isVisible():
                self.report_window.refresh_data()

    # --- Dialog Windows ---

    def open_reports(self):
        if not self.report_window:
            self.report_window = ReportWindow()
            self.report_window.data_changed.connect(self._on_child_data_changed)
        self.report_window.show()
        self.report_window.raise_()
        self.report_window.activateWindow()

    def open_settings(self):
        if not self.settings_dialog:
            self.settings_dialog = SettingsDialog()
            self.settings_dialog.settings_saved.connect(self._on_settings_saved)
        self.settings_dialog.show()
        self.settings_dialog.raise_()
        self.settings_dialog.activateWindow()

    def _on_child_data_changed(self):
        self._update_display()
        self.state_changed.emit()

    def _on_settings_saved(self):
        self._setup_window_flags()
        self._apply_theme()
        self._check_auto_clock_in()
        self._update_display()
        self.state_changed.emit()

    # --- Widget Controls ---

    def _toggle_always_on_top(self):
        is_top = not config.get("always_on_top", True)
        config.set("always_on_top", is_top)
        self._setup_window_flags()
        self.show()

    def _toggle_collapse(self):
        collapsed = not self.body_widget.isHidden()
        if collapsed:
            self.body_widget.hide()
            self.btn_collapse.setText("🔽")
        else:
            self.body_widget.show()
            self.btn_collapse.setText("🔼")
        config.set("collapsed", collapsed)
        self.adjustSize()

    def _on_close_clicked(self):
        if config.get("minimize_to_tray_on_close", True):
            self.hide()
        else:
            QApplication.quit()

    # --- Dragging & Screen Edge Snapping ---

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_start_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._dragging and event.buttons() == Qt.MouseButton.LeftButton:
            new_pos = event.globalPosition().toPoint() - self._drag_start_pos

            if config.get("snap_to_edges", True):
                # Edge snapping within 20px
                screen = QGuiApplication.screenAt(event.globalPosition().toPoint())
                if screen:
                    geom = screen.availableGeometry()
                    snap_dist = 20
                    # Left snap
                    if abs(new_pos.x() - geom.left()) < snap_dist:
                        new_pos.setX(geom.left())
                    # Right snap
                    elif abs(new_pos.x() + self.width() - geom.right()) < snap_dist:
                        new_pos.setX(geom.right() - self.width())
                    # Top snap
                    if abs(new_pos.y() - geom.top()) < snap_dist:
                        new_pos.setY(geom.top())
                    # Bottom snap
                    elif abs(new_pos.y() + self.height() - geom.bottom()) < snap_dist:
                        new_pos.setY(geom.bottom() - self.height())

            self.move(new_pos)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self._dragging:
            self._dragging = False
            # Save position
            config.set("widget_x", self.x(), auto_save=False)
            config.set("widget_y", self.y(), auto_save=True)
            event.accept()

    def _restore_position(self):
        wx = config.get("widget_x", -1)
        wy = config.get("widget_y", -1)

        screen = QGuiApplication.primaryScreen()
        if screen:
            geom = screen.availableGeometry()
            if wx >= 0 and wy >= 0 and wx < geom.right() and wy < geom.bottom():
                self.move(wx, wy)
            else:
                # Default position: Top Right Corner with margin
                default_x = geom.right() - self.width() - 30
                default_y = geom.top() + 40
                self.move(default_x, default_y)

    def closeEvent(self, event):
        """Auto clocks out on app exit/shutdown if enabled."""
        if config.get("auto_clock_out_on_shutdown", True):
            active = db.get_active_session()
            if active:
                db.clock_out("Auto Clock-Out on shutdown/exit")
                self.state_changed.emit()
        event.accept()
