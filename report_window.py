"""
Monthly Reports, Interactive Calendar, and Timesheet management window.
"""

import os
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtGui import QColor, QCursor, QFont
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from config import config
from db import db
from excel_exporter import excel_exporter
from manual_entry_dialog import ManualEntryDialog
from theme import get_theme_stylesheet


class DayCardWidget(QFrame):
    """Interactive day card in the monthly calendar grid."""

    clicked = Signal(date)

    def __init__(
        self,
        card_date: date,
        is_current_month: bool,
        is_today: bool,
        work_sec: float,
        is_selected: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self.card_date = card_date
        self.is_current_month = is_current_month
        self.is_today = is_today
        self.work_sec = work_sec
        self.is_selected = is_selected

        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(80, 70)

        self._init_ui()
        self._apply_style()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(2)

        # Header: Day number + status indicator dot
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)

        self.lbl_day_num = QLabel(str(self.card_date.day))
        self.lbl_day_num.setStyleSheet("font-weight: bold; font-size: 12px;")

        self.lbl_indicator = QLabel()
        self.lbl_indicator.setFixedSize(8, 8)

        header_row.addWidget(self.lbl_day_num)
        header_row.addStretch()
        header_row.addWidget(self.lbl_indicator)
        layout.addLayout(header_row)

        layout.addStretch()

        # Hours text
        work_hours = self.work_sec / 3600.0
        if self.is_current_month and self.work_sec > 60:
            h = int(self.work_sec // 3600)
            m = int((self.work_sec % 3600) // 60)
            self.lbl_hours = QLabel(f"{h}h {m:02d}m")
            self.lbl_hours.setStyleSheet("font-size: 11px; font-weight: 600;")
        elif self.is_current_month:
            self.lbl_hours = QLabel("-")
            self.lbl_hours.setStyleSheet("color: #64748B; font-size: 11px;")
        else:
            self.lbl_hours = QLabel("")

        self.lbl_hours.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_hours)

    def _apply_style(self):
        daily_target_hours = float(config.get("daily_target_hours", 8.0))
        daily_min_hours = float(config.get("daily_min_hours", 4.0))
        work_hours = self.work_sec / 3600.0
        work_days = config.get("work_days", [5, 6, 0, 1, 2])
        is_weekend = self.card_date.weekday() not in work_days

        # Determine border color & background
        if self.is_selected:
            border = "2px solid #38BDF8"
            bg = "#1E293B"
        elif self.is_today:
            border = "2px solid #2563EB"
            bg = "#1E293B"
        else:
            border = "1px solid #334155"
            bg = "#1E293B" if self.is_current_month else "rgba(15, 23, 42, 0.4)"

        # Text and status dot colors
        if not self.is_current_month:
            self.lbl_day_num.setStyleSheet("color: #475569; font-size: 11px;")
            self.lbl_indicator.setStyleSheet("background: transparent;")
        elif work_hours >= daily_target_hours:
            self.lbl_day_num.setStyleSheet("color: #F8FAFC; font-weight: bold;")
            self.lbl_indicator.setStyleSheet("background-color: #10B981; border-radius: 4px;")
            self.lbl_hours.setStyleSheet("color: #34D399; font-weight: bold; font-size: 11px;")
        elif work_hours >= daily_min_hours:
            self.lbl_day_num.setStyleSheet("color: #F8FAFC; font-weight: bold;")
            self.lbl_indicator.setStyleSheet("background-color: #F59E0B; border-radius: 4px;")
            self.lbl_hours.setStyleSheet("color: #FBBF24; font-weight: bold; font-size: 11px;")
        elif self.work_sec > 60:
            self.lbl_day_num.setStyleSheet("color: #F8FAFC; font-weight: bold;")
            self.lbl_indicator.setStyleSheet("background-color: #EF4444; border-radius: 4px;")
            self.lbl_hours.setStyleSheet("color: #F87171; font-weight: bold; font-size: 11px;")
        else:
            if is_weekend:
                self.lbl_day_num.setStyleSheet("color: #64748B; font-weight: normal;")
            else:
                self.lbl_day_num.setStyleSheet("color: #94A3B8; font-weight: normal;")
            self.lbl_indicator.setStyleSheet("background: transparent;")

        self.setStyleSheet(
            f"""
            QFrame {{
                background-color: {bg};
                border: {border};
                border-radius: 8px;
            }}
            QFrame:hover {{
                border: 2px solid #38BDF8;
            }}
            """
        )

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.card_date)
        super().mousePressEvent(event)


class ReportWindow(QDialog):
    """Complete Calendar & Monthly Analytics dialog."""

    data_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Office Time Tracker - Monthly Calendar & Reports")
        self.resize(1020, 680)
        self.setModal(False)
        self.setStyleSheet(get_theme_stylesheet(config.get("theme", "dark")))

        today = date.today()
        self.current_year = today.year
        self.current_month = today.month
        self.selected_date = today

        self._init_ui()
        self.refresh_data()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(14)
        main_layout.setContentsMargins(18, 18, 18, 18)

        # 1. Top Navigation & Action Bar
        top_bar = QHBoxLayout()
        top_bar.setSpacing(12)

        # Month Navigation
        self.btn_prev_month = QPushButton("◀ Prev")
        self.btn_prev_month.clicked.connect(self._on_prev_month)

        self.lbl_month_title = QLabel("August 2026")
        self.lbl_month_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #38BDF8;")
        self.lbl_month_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_next_month = QPushButton("Next ▶")
        self.btn_next_month.clicked.connect(self._on_next_month)

        self.btn_today = QPushButton("Today")
        self.btn_today.clicked.connect(self._on_go_today)

        top_bar.addWidget(self.btn_prev_month)
        top_bar.addWidget(self.lbl_month_title)
        top_bar.addWidget(self.btn_next_month)
        top_bar.addWidget(self.btn_today)
        top_bar.addStretch()

        # Export & Add Entry Buttons
        self.btn_export = QPushButton("📥 Export to Excel (.xlsx)")
        self.btn_export.setObjectName("PrimaryBtn")
        self.btn_export.clicked.connect(self._on_export_excel)

        self.btn_add_session = QPushButton("➕ Log Manual Session")
        self.btn_add_session.clicked.connect(self._on_add_manual_session)

        top_bar.addWidget(self.btn_export)
        top_bar.addWidget(self.btn_add_session)

        main_layout.addLayout(top_bar)

        # 2. KPI Metrics Summary Cards (5 cards)
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(10)

        self.card_total = self._create_kpi_card("TOTAL WORKED", "0.0 hrs", "#38BDF8")
        self.card_target = self._create_kpi_card("EXPECTED TARGET", "0.0 hrs", "#94A3B8")
        self.card_balance = self._create_kpi_card("OVERTIME / DEFICIT", "+0.0 hrs", "#34D399")
        self.card_days = self._create_kpi_card("DAYS WORKED", "0 / 0 days", "#FBBF24")
        self.card_avg = self._create_kpi_card("DAILY AVERAGE", "0.0 hrs/day", "#A78BFA")

        kpi_layout.addWidget(self.card_total)
        kpi_layout.addWidget(self.card_target)
        kpi_layout.addWidget(self.card_balance)
        kpi_layout.addWidget(self.card_days)
        kpi_layout.addWidget(self.card_avg)

        main_layout.addLayout(kpi_layout)

        # 3. Main Splitter: Left Calendar (65%), Right Day Details & Week Stats (35%)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: Calendar Container
        cal_container = QWidget()
        cal_layout = QVBoxLayout(cal_container)
        cal_layout.setContentsMargins(0, 0, 0, 0)
        cal_layout.setSpacing(6)

        # Day of Week Headers (Mon-Sun)
        days_header_layout = QHBoxLayout()
        days_header_layout.setSpacing(6)
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for d_name in day_names:
            lbl = QLabel(d_name)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(
                "font-weight: bold; font-size: 11px; color: #94A3B8; padding: 4px; background-color: #1E293B; border-radius: 4px;"
            )
            days_header_layout.addWidget(lbl)
        cal_layout.addLayout(days_header_layout)

        # Calendar Grid
        self.cal_grid_widget = QWidget()
        self.cal_grid = QGridLayout(self.cal_grid_widget)
        self.cal_grid.setSpacing(6)
        self.cal_grid.setContentsMargins(0, 0, 0, 0)
        cal_layout.addWidget(self.cal_grid_widget)

        # Legend Bar
        legend_layout = QHBoxLayout()
        legend_layout.setSpacing(14)
        legend_layout.addStretch()
        legend_layout.addWidget(self._create_legend_item("#10B981", "Target Met (8h+)"))
        legend_layout.addWidget(self._create_legend_item("#F59E0B", "Min Met (4h+)"))
        legend_layout.addWidget(self._create_legend_item("#EF4444", "Under Min (<4h)"))
        legend_layout.addWidget(self._create_legend_item("#475569", "Off / Weekend"))
        legend_layout.addStretch()
        cal_layout.addLayout(legend_layout)

        splitter.addWidget(cal_container)

        # Right: Day Details & Weekly Breakdown Tabs
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        # Day Details Card
        day_details_card = QFrame()
        day_details_card.setObjectName("CardFrame")
        day_card_layout = QVBoxLayout(day_details_card)
        day_card_layout.setContentsMargins(12, 12, 12, 12)
        day_card_layout.setSpacing(8)

        # Date header in details
        detail_header = QHBoxLayout()
        self.lbl_selected_day_title = QLabel("Selected Day Details")
        self.lbl_selected_day_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #38BDF8;")
        self.lbl_selected_day_hours = QLabel("0h 00m")
        self.lbl_selected_day_hours.setStyleSheet("font-size: 13px; font-weight: bold; color: #34D399;")
        detail_header.addWidget(self.lbl_selected_day_title)
        detail_header.addStretch()
        detail_header.addWidget(self.lbl_selected_day_hours)
        day_card_layout.addLayout(detail_header)

        # Sessions Table
        self.table_sessions = QTableWidget()
        self.table_sessions.setColumnCount(4)
        self.table_sessions.setHorizontalHeaderLabels(["In", "Out", "Break", "Work"])
        self.table_sessions.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_sessions.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_sessions.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table_sessions.setMinimumHeight(140)
        day_card_layout.addWidget(self.table_sessions)

        # Table Action Buttons
        session_btn_layout = QHBoxLayout()
        session_btn_layout.setSpacing(6)

        self.btn_edit_session = QPushButton("✏️ Edit")
        self.btn_edit_session.clicked.connect(self._on_edit_selected_session)

        self.btn_delete_session = QPushButton("🗑️ Delete")
        self.btn_delete_session.clicked.connect(self._on_delete_selected_session)

        session_btn_layout.addStretch()
        session_btn_layout.addWidget(self.btn_edit_session)
        session_btn_layout.addWidget(self.btn_delete_session)
        day_card_layout.addLayout(session_btn_layout)

        right_layout.addWidget(day_details_card)

        # Weekly Summary Breakdown Table
        week_card = QFrame()
        week_card.setObjectName("CardFrame")
        week_layout = QVBoxLayout(week_card)
        week_layout.setContentsMargins(12, 12, 12, 12)
        week_layout.setSpacing(6)

        lbl_week_title = QLabel("Weekly Breakdown (Target: 36h)")
        lbl_week_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #A78BFA;")
        week_layout.addWidget(lbl_week_title)

        self.table_weeks = QTableWidget()
        self.table_weeks.setColumnCount(4)
        self.table_weeks.setHorizontalHeaderLabels(["Week", "Dates", "Worked", "Variance"])
        self.table_weeks.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_weeks.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_weeks.setMaximumHeight(150)
        week_layout.addWidget(self.table_weeks)

        right_layout.addWidget(week_card)

        splitter.addWidget(right_container)
        splitter.setStretchFactor(0, 65)
        splitter.setStretchFactor(1, 35)

        main_layout.addWidget(splitter)

    def _create_kpi_card(self, title: str, initial_val: str, accent_color: str) -> QFrame:
        card = QFrame()
        card.setObjectName("CardFrame")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(2)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-size: 10px; font-weight: bold; color: #64748B;")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_val = QLabel(initial_val)
        lbl_val.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {accent_color};")
        lbl_val.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(lbl_title)
        layout.addWidget(lbl_val)
        card.value_label = lbl_val
        return card

    def _create_legend_item(self, color_hex: str, label_text: str) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        dot = QLabel()
        dot.setFixedSize(10, 10)
        dot.setStyleSheet(f"background-color: {color_hex}; border-radius: 5px;")

        lbl = QLabel(label_text)
        lbl.setStyleSheet("font-size: 11px; color: #94A3B8;")

        layout.addWidget(dot)
        layout.addWidget(lbl)
        return widget

    def refresh_data(self):
        """Reloads month summary data, updates calendar cards, and populates side panels."""
        month_data = db.get_month_summary(self.current_year, self.current_month)
        month_name = month_data["month_name"]
        self.lbl_month_title.setText(f"{month_name} {self.current_year}")

        # Update KPI Cards
        self.card_total.value_label.setText(f"{month_data['total_month_work_hours']:.1f} hrs")
        self.card_target.value_label.setText(f"{month_data['expected_target_hours']:.1f} hrs")

        balance = month_data["balance_hours"]
        sign = "+" if balance >= 0 else ""
        self.card_balance.value_label.setText(f"{sign}{balance:.1f} hrs")
        self.card_balance.value_label.setStyleSheet(
            f"font-size: 15px; font-weight: bold; color: {'#34D399' if balance >= 0 else '#EF4444'};"
        )

        self.card_days.value_label.setText(
            f"{month_data['active_days_count']} / {month_data['weekday_count']} days"
        )
        self.card_avg.value_label.setText(f"{month_data['avg_hours_per_active_day']:.1f} hrs/day")

        # Build Calendar Grid
        self._rebuild_calendar_grid(month_data)

        # Update Day Details Table
        self._load_day_details(self.selected_date)

        # Update Weekly Summary Table
        self._load_weekly_table(month_data["weeks"])

    def _rebuild_calendar_grid(self, month_data: Dict):
        # Clear existing grid
        while self.cal_grid.count():
            item = self.cal_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        year = self.current_year
        month = self.current_month
        first_day_of_month = date(year, month, 1)

        # Find Monday of first week
        start_cal_date = first_day_of_month - timedelta(days=first_day_of_month.weekday())
        curr_date = start_cal_date
        today = date.today()

        daily_data = month_data["daily_data"]

        for row in range(6):
            for col in range(7):
                is_curr_m = (curr_date.month == month and curr_date.year == year)
                is_today = (curr_date == today)
                is_sel = (curr_date == self.selected_date)

                date_str = curr_date.strftime("%Y-%m-%d")
                if is_curr_m and date_str in daily_data:
                    work_sec = daily_data[date_str]["work_sec"]
                else:
                    work_sec = 0.0

                card = DayCardWidget(
                    card_date=curr_date,
                    is_current_month=is_curr_m,
                    is_today=is_today,
                    work_sec=work_sec,
                    is_selected=is_sel,
                )
                card.clicked.connect(self._on_day_clicked)
                self.cal_grid.addWidget(card, row, col)

                curr_date += timedelta(days=1)

            # If we've passed the month and finished the week, stop
            if curr_date.month != month and row >= 4:
                break

    def _on_day_clicked(self, clicked_date: date):
        self.selected_date = clicked_date
        self.refresh_data()

    def _load_day_details(self, target_date: date):
        date_str = target_date.strftime("%Y-%m-%d")
        self.lbl_selected_day_title.setText(target_date.strftime("%A, %b %d, %Y"))

        day_sum = db.get_today_summary(target_date)
        work_sec = day_sum["total_work_sec"]
        h = int(work_sec // 3600)
        m = int((work_sec % 3600) // 60)
        self.lbl_selected_day_hours.setText(f"{h}h {m:02d}m ({work_sec/3600.0:.2f}h)")

        sessions = day_sum["sessions"]
        self.table_sessions.setRowCount(len(sessions))

        for row_idx, s in enumerate(sessions):
            t_in = datetime.fromisoformat(s["clock_in"]).strftime("%H:%M")
            t_out = datetime.fromisoformat(s["clock_out"]).strftime("%H:%M") if s.get("clock_out") else "Active"
            b_mins = int(round(float(s.get("break_duration_seconds", 0.0) or 0.0) / 60.0))
            w_sec, _ = db.calculate_session_duration(s)
            w_str = f"{int(w_sec//3600)}h {int((w_sec%3600)//60):02d}m"

            item_in = QTableWidgetItem(t_in)
            item_out = QTableWidgetItem(t_out)
            item_break = QTableWidgetItem(f"{b_mins}m")
            item_work = QTableWidgetItem(w_str)

            for item in (item_in, item_out, item_break, item_work):
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setData(Qt.ItemDataRole.UserRole, s["id"])

            self.table_sessions.setItem(row_idx, 0, item_in)
            self.table_sessions.setItem(row_idx, 1, item_out)
            self.table_sessions.setItem(row_idx, 2, item_break)
            self.table_sessions.setItem(row_idx, 3, item_work)

    def _load_weekly_table(self, weeks: List[Dict]):
        self.table_weeks.setRowCount(len(weeks))
        for r, w in enumerate(weeks):
            item_num = QTableWidgetItem(f"W{w['week_num']}")
            item_range = QTableWidgetItem(w["range_label"])
            item_hours = QTableWidgetItem(f"{w['work_hours']:.1f}h")

            var_val = w["work_hours"] - w["target_hours"]
            var_str = f"{'+' if var_val >= 0 else ''}{var_val:.1f}h"
            item_var = QTableWidgetItem(var_str)

            if var_val >= 0:
                item_var.setForeground(QColor("#34D399"))
            else:
                item_var.setForeground(QColor("#F87171"))

            for item in (item_num, item_range, item_hours, item_var):
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            self.table_weeks.setItem(r, 0, item_num)
            self.table_weeks.setItem(r, 1, item_range)
            self.table_weeks.setItem(r, 2, item_hours)
            self.table_weeks.setItem(r, 3, item_var)

    # --- Actions ---

    def _on_prev_month(self):
        if self.current_month == 1:
            self.current_month = 12
            self.current_year -= 1
        else:
            self.current_month -= 1
        self.refresh_data()

    def _on_next_month(self):
        if self.current_month == 12:
            self.current_month = 1
            self.current_year += 1
        else:
            self.current_month += 1
        self.refresh_data()

    def _on_go_today(self):
        today = date.today()
        self.current_year = today.year
        self.current_month = today.month
        self.selected_date = today
        self.refresh_data()

    def _on_add_manual_session(self):
        dlg = ManualEntryDialog(self, default_date=self.selected_date)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh_data()
            self.data_changed.emit()

    def _on_edit_selected_session(self):
        sel_rows = self.table_sessions.selectionModel().selectedRows()
        if not sel_rows:
            QMessageBox.information(self, "Select Session", "Please select a session row to edit.")
            return

        row = sel_rows[0].row()
        item = self.table_sessions.item(row, 0)
        session_id = item.data(Qt.ItemDataRole.UserRole)

        dlg = ManualEntryDialog(self, session_id=session_id)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh_data()
            self.data_changed.emit()

    def _on_delete_selected_session(self):
        sel_rows = self.table_sessions.selectionModel().selectedRows()
        if not sel_rows:
            QMessageBox.information(self, "Select Session", "Please select a session row to delete.")
            return

        row = sel_rows[0].row()
        item = self.table_sessions.item(row, 0)
        session_id = item.data(Qt.ItemDataRole.UserRole)

        res = QMessageBox.question(
            self,
            "Confirm Delete",
            "Are you sure you want to delete this work session?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if res == QMessageBox.StandardButton.Yes:
            db.delete_session(session_id)
            self.refresh_data()
            self.data_changed.emit()

    def _on_export_excel(self):
        from config import get_data_dir

        default_filename = f"Time_Report_{self.current_year}_{self.current_month:02d}.xlsx"
        suggested_path = get_data_dir() / "reports" / default_filename
        suggested_path.parent.mkdir(parents=True, exist_ok=True)

        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save Excel Report", str(suggested_path), "Excel Files (*.xlsx)"
        )
        if not save_path:
            return

        from pathlib import Path

        out_path = Path(save_path)
        try:
            excel_exporter.export_monthly_report(self.current_year, self.current_month, out_path)
            res = QMessageBox.question(
                self,
                "Export Complete",
                f"Report exported successfully to:\n{out_path}\n\nWould you like to open it now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if res == QMessageBox.StandardButton.Yes:
                os.startfile(str(out_path))
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Failed to generate Excel report:\n{e}")
