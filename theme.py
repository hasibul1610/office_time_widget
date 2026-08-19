"""
Theme and styling definitions for Office Time Widget.
Provides modern dark glass and clean light styles with scalable typography.
"""

from typing import Dict


def get_clock_font_size(size_name: str = "large") -> int:
    sizes = {
        "standard": 50,
        "large": 64,
        "xlarge": 76,
        "jumbo": 88,
    }
    return sizes.get(size_name.lower(), 64)


def get_theme_stylesheet(theme_name: str = "dark", clock_size: str = "large") -> str:
    """Returns the CSS stylesheet string for the chosen theme and clock size."""
    clock_px = get_clock_font_size(clock_size)
    sec_px = max(18, clock_px // 3)

    if theme_name == "light":
        return f"""
QWidget#MainWidget {{
    background-color: rgba(255, 255, 255, 0.96);
    border: 1px solid rgba(0, 0, 0, 0.12);
    border-radius: 20px;
}}

QDialog, QMainWindow {{
    background-color: #F8FAFC;
    color: #0F172A;
}}

QLabel {{
    color: #0F172A;
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
}}

QLabel#ClockLabel {{
    color: #0F172A;
    font-size: {clock_px}px;
    font-weight: 800;
    letter-spacing: 1px;
}}

QLabel#SecondsLabel {{
    color: #475569;
    font-size: {sec_px}px;
    font-weight: 700;
}}

QLabel#DateLabel {{
    color: #0284C7;
    font-size: 15px;
    font-weight: 700;
}}

QLabel#StatusBadge {{
    border-radius: 10px;
    padding: 4px 12px;
    font-size: 12px;
    font-weight: bold;
}}

QLabel#StatusBadgeIdle {{
    background-color: #E2E8F0;
    color: #64748B;
}}

QLabel#StatusBadgeWorking {{
    background-color: #DCFCE7;
    color: #166534;
}}

QLabel#StatusBadgeBreak {{
    background-color: #FEF3C7;
    color: #92400E;
}}

QLabel#SectionTitle {{
    color: #64748B;
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}

/* Push Buttons */
QPushButton {{
    background-color: #FFFFFF;
    color: #0F172A;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    padding: 8px 16px;
    font-family: 'Segoe UI', sans-serif;
    font-size: 13px;
    font-weight: 600;
}}

QPushButton:hover {{
    background-color: #F1F5F9;
    border-color: #94A3B8;
}}

QPushButton:pressed {{
    background-color: #E2E8F0;
}}

QPushButton#PrimaryBtn {{
    background-color: #2563EB;
    border: 1px solid #1D4ED8;
    color: #FFFFFF;
    font-size: 14px;
    font-weight: bold;
    padding: 10px 18px;
    border-radius: 10px;
}}

QPushButton#PrimaryBtn:hover {{
    background-color: #1D4ED8;
}}

QPushButton#StopBtn {{
    background-color: #DC2626;
    border: 1px solid #B91C1C;
    color: #FFFFFF;
    font-size: 14px;
    font-weight: bold;
    padding: 10px 18px;
    border-radius: 10px;
}}

QPushButton#StopBtn:hover {{
    background-color: #B91C1C;
}}

QPushButton#BreakBtn {{
    background-color: #D97706;
    border: 1px solid #B45309;
    color: #FFFFFF;
    font-size: 14px;
    font-weight: bold;
    padding: 10px 18px;
    border-radius: 10px;
}}

QPushButton#BreakBtn:hover {{
    background-color: #B45309;
}}

QPushButton#ResumeBtn {{
    background-color: #059669;
    border: 1px solid #047857;
    color: #FFFFFF;
    font-size: 14px;
    font-weight: bold;
    padding: 10px 18px;
    border-radius: 10px;
}}

QPushButton#ResumeBtn:hover {{
    background-color: #047857;
}}

QPushButton#IconButton {{
    background-color: transparent;
    border: none;
    border-radius: 6px;
    padding: 4px;
    color: #64748B;
    font-size: 15px;
}}

QPushButton#IconButton:hover {{
    background-color: rgba(0, 0, 0, 0.05);
    color: #0F172A;
}}

/* Progress Bars */
QProgressBar {{
    background-color: #E2E8F0;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    text-align: center;
    color: transparent;
    height: 10px;
    max-height: 10px;
}}

QProgressBar::chunk {{
    border-radius: 5px;
}}

QProgressBar#MinBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284C7, stop:1 #2563EB);
}}

QProgressBar#TargetBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #059669, stop:1 #10B981);
}}

QProgressBar#WeekBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7C3AED, stop:1 #8B5CF6);
}}

/* Input Fields & Spinboxes */
QLineEdit, QDateEdit, QTimeEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit {{
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 6px 10px;
    color: #0F172A;
    font-family: 'Segoe UI', sans-serif;
    font-size: 13px;
}}

QLineEdit:focus, QDateEdit:focus, QTimeEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QTextEdit:focus {{
    border: 1px solid #2563EB;
}}

/* Tables */
QTableWidget {{
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    gridline-color: #E2E8F0;
    color: #0F172A;
    font-family: 'Segoe UI', sans-serif;
    font-size: 12px;
    selection-background-color: #2563EB;
    selection-color: #FFFFFF;
}}

QHeaderView::section {{
    background-color: #F1F5F9;
    color: #475569;
    padding: 6px;
    font-weight: 600;
    font-size: 12px;
    border: none;
    border-bottom: 1px solid #CBD5E1;
}}

/* Cards */
QFrame#CardFrame {{
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
}}

QFrame#HighlightCard {{
    background-color: #EFF6FF;
    border: 1px solid #3B82F6;
    border-radius: 12px;
}}

/* Tabs */
QTabWidget::pane {{
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    background: #FFFFFF;
}}

QTabBar::tab {{
    background: #F1F5F9;
    color: #64748B;
    padding: 8px 16px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
}}

QTabBar::tab:selected {{
    background: #FFFFFF;
    color: #0284C7;
    font-weight: bold;
    border-bottom: 2px solid #0284C7;
}}

QCheckBox {{
    color: #0F172A;
    spacing: 8px;
    font-size: 13px;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #CBD5E1;
    background: #FFFFFF;
}}

QCheckBox::indicator:checked {{
    background-color: #2563EB;
    border-color: #2563EB;
}}

QSlider::groove:horizontal {{
    height: 6px;
    background: #E2E8F0;
    border-radius: 3px;
}}

QSlider::sub-page:horizontal {{
    background: #2563EB;
    border-radius: 3px;
}}

QSlider::handle:horizontal {{
    background: #0F172A;
    width: 16px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 8px;
}}
"""

    return f"""
QWidget#MainWidget {{
    background-color: rgba(24, 28, 38, 0.94);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 20px;
}}

QDialog, QMainWindow {{
    background-color: #0F172A;
    color: #F8FAFC;
}}

QLabel {{
    color: #F1F5F9;
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
}}

QLabel#ClockLabel {{
    color: #FFFFFF;
    font-size: {clock_px}px;
    font-weight: 800;
    letter-spacing: 1px;
}}

QLabel#SecondsLabel {{
    color: #94A3B8;
    font-size: {sec_px}px;
    font-weight: 700;
}}

QLabel#DateLabel {{
    color: #38BDF8;
    font-size: 15px;
    font-weight: 700;
}}

QLabel#StatusBadge {{
    border-radius: 10px;
    padding: 4px 12px;
    font-size: 12px;
    font-weight: bold;
}}

QLabel#StatusBadgeIdle {{
    background-color: #334155;
    color: #94A3B8;
}}

QLabel#StatusBadgeWorking {{
    background-color: #065F46;
    color: #34D399;
}}

QLabel#StatusBadgeBreak {{
    background-color: #78350F;
    color: #FBBF24;
}}

QLabel#SectionTitle {{
    color: #94A3B8;
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}

/* Push Buttons */
QPushButton {{
    background-color: #1E293B;
    color: #F8FAFC;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 8px 16px;
    font-family: 'Segoe UI', sans-serif;
    font-size: 13px;
    font-weight: 600;
}}

QPushButton:hover {{
    background-color: #334155;
    border-color: #475569;
}}

QPushButton:pressed {{
    background-color: #0F172A;
}}

QPushButton#PrimaryBtn {{
    background-color: #2563EB;
    border: 1px solid #3B82F6;
    color: #FFFFFF;
    font-size: 14px;
    font-weight: bold;
    padding: 10px 18px;
    border-radius: 10px;
}}

QPushButton#PrimaryBtn:hover {{
    background-color: #1D4ED8;
}}

QPushButton#StopBtn {{
    background-color: #DC2626;
    border: 1px solid #EF4444;
    color: #FFFFFF;
    font-size: 14px;
    font-weight: bold;
    padding: 10px 18px;
    border-radius: 10px;
}}

QPushButton#StopBtn:hover {{
    background-color: #B91C1C;
}}

QPushButton#BreakBtn {{
    background-color: #D97706;
    border: 1px solid #F59E0B;
    color: #FFFFFF;
    font-size: 14px;
    font-weight: bold;
    padding: 10px 18px;
    border-radius: 10px;
}}

QPushButton#BreakBtn:hover {{
    background-color: #B45309;
}}

QPushButton#ResumeBtn {{
    background-color: #059669;
    border: 1px solid #10B981;
    color: #FFFFFF;
    font-size: 14px;
    font-weight: bold;
    padding: 10px 18px;
    border-radius: 10px;
}}

QPushButton#ResumeBtn:hover {{
    background-color: #047857;
}}

QPushButton#IconButton {{
    background-color: transparent;
    border: none;
    border-radius: 6px;
    padding: 4px;
    color: #94A3B8;
    font-size: 15px;
}}

QPushButton#IconButton:hover {{
    background-color: rgba(255, 255, 255, 0.1);
    color: #F8FAFC;
}}

/* Progress Bars */
QProgressBar {{
    background-color: #0F172A;
    border: 1px solid #1E293B;
    border-radius: 6px;
    text-align: center;
    color: transparent;
    height: 10px;
    max-height: 10px;
}}

QProgressBar::chunk {{
    border-radius: 5px;
}}

QProgressBar#MinBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #06B6D4, stop:1 #3B82F6);
}}

QProgressBar#TargetBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10B981, stop:1 #34D399);
}}

QProgressBar#WeekBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8B5CF6, stop:1 #A78BFA);
}}

/* Input Fields & Spinboxes */
QLineEdit, QDateEdit, QTimeEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit {{
    background-color: #1E293B;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 10px;
    color: #F8FAFC;
    font-family: 'Segoe UI', sans-serif;
    font-size: 13px;
}}

QLineEdit:focus, QDateEdit:focus, QTimeEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QTextEdit:focus {{
    border: 1px solid #3B82F6;
}}

QComboBox::drop-down {{
    border: none;
    padding-right: 8px;
}}

/* Tables */
QTableWidget {{
    background-color: #1E293B;
    border: 1px solid #334155;
    border-radius: 8px;
    gridline-color: #334155;
    color: #F8FAFC;
    font-family: 'Segoe UI', sans-serif;
    font-size: 12px;
    selection-background-color: #2563EB;
    selection-color: #FFFFFF;
}}

QHeaderView::section {{
    background-color: #0F172A;
    color: #94A3B8;
    padding: 6px;
    font-weight: 600;
    font-size: 12px;
    border: none;
    border-bottom: 1px solid #334155;
}}

/* Cards & Frames */
QFrame#CardFrame {{
    background-color: #1E293B;
    border: 1px solid #334155;
    border-radius: 12px;
}}

QFrame#HighlightCard {{
    background-color: #1E293B;
    border: 1px solid #3B82F6;
    border-radius: 12px;
}}

/* Scrollbars */
QScrollBar:vertical {{
    border: none;
    background: #0F172A;
    width: 8px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical {{
    background: #334155;
    min-height: 20px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical:hover {{
    background: #475569;
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

/* Tab Widget */
QTabWidget::pane {{
    border: 1px solid #334155;
    border-radius: 8px;
    background: #0F172A;
}}

QTabBar::tab {{
    background: #1E293B;
    color: #94A3B8;
    padding: 8px 16px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
}}

QTabBar::tab:selected {{
    background: #0F172A;
    color: #38BDF8;
    font-weight: bold;
    border-bottom: 2px solid #38BDF8;
}}

/* Checkbox */
QCheckBox {{
    color: #F1F5F9;
    spacing: 8px;
    font-size: 13px;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #475569;
    background: #1E293B;
}}

QCheckBox::indicator:checked {{
    background-color: #2563EB;
    border-color: #3B82F6;
}}

/* Slider */
QSlider::groove:horizontal {{
    height: 6px;
    background: #1E293B;
    border-radius: 3px;
}}

QSlider::sub-page:horizontal {{
    background: #2563EB;
    border-radius: 3px;
}}

QSlider::handle:horizontal {{
    background: #FFFFFF;
    width: 16px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 8px;
}}
"""
