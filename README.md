# ⏱️ Office Time Widget (Windows)

A complete, modern, and portable desktop **Office Time Widget** built with **Python**, **PySide6 (Qt6)**, and **SQLite**.

Designed for office professionals who need seamless daily and weekly time tracking, milestone targets, monthly calendar reporting, and Excel export capabilities.

---

## ✨ Features

- **Borderless & Draggable Desktop Widget**: Modern translucent acrylic dark/light theme, soft drop shadows, and automatic screen edge snapping.
- **Large Digital Clock & Date**: Crisp typography with 12/24-hour modes, optional seconds ticker, and formatted day/date display.
- **Punch In / Punch Out & Breaks**:
  - Live session stopwatch counter.
  - One-click Clock In / Clock Out.
  - Dedicated Break tracker with cumulative pause calculations.
- **Milestone Progress Tracking**:
  - 🎯 **Daily Minimum**: Target 4.0 hours with checkmark completion indicator.
  - 🎯 **Daily Standard**: Target 8.0 hours with live overtime calculation (+hh:mm).
  - 🎯 **Weekly Target**: Target 36.0 hours (Monday–Sunday) with remaining balance indicator.
- **Dynamic Advice Ticker**: Real-time ticker displaying hours remaining to minimum, daily target, or overtime status.
- **Monthly Interactive Calendar & Reports**:
  - Visual monthly calendar grid with color-coded day badges (🟢 $\ge 8$h, 🟡 $4-8$h, 🔴 $<4$h, ⚪ Weekend).
  - KPI Stat Cards: Total Hours, Target Hours, Overtime/Deficit Balance, Days Worked, Daily Average.
  - Day details side-drawer with session listings, Add/Edit/Delete capabilities.
  - Weekly summary breakdown table.
- **Executive Excel Reports (.xlsx)**:
  - Generates polished multi-sheet Excel reports with executive KPI cards, weekly summary tables, and full daily time logs with `=SUM(...)` formulas.
- **Windows System Tray Integration**:
  - Dynamic tray icon with status dot (Green for Working, Amber for Break, Slate for Idle).
  - Tray tooltip with live today and week progress summary.
  - Context menu with quick Clock In/Out, Take Break, Show/Hide Widget, Reports, Settings, and Exit.
  - Milestone Balloon/Toast notifications when crossing 4h, 8h, or 36h milestones.
- **Windows Auto-Start**:
  - Toggle auto-start directly in Settings to automatically launch at Windows startup via `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`.
- **JSON Configuration & Portable SQLite Database**:
  - Stored next to executable for 100% portability (with fallback to `%APPDATA%`).
- **Single Portable Executable**:
  - Compiles into a standalone `OfficeTimeWidget.exe` using PyInstaller.

---

## 🚀 Quick Start

### Running from Source
```bash
# Run tests
python -m unittest discover tests

# Launch application
python main.py
```

### Building Portable Executable (.exe)
```bash
python build_portable.py
```
The standalone executable will be located at `dist/OfficeTimeWidget.exe`.

---

## ⚙️ Configuration (`settings.json`)

| Setting | Default | Description |
|---|---|---|
| `daily_min_hours` | `4.0` | Daily minimum milestone (hours) |
| `daily_target_hours` | `8.0` | Daily target milestone (hours) |
| `weekly_target_hours` | `36.0` | Weekly target milestone (hours) |
| `theme` | `"dark"` | UI theme (`"dark"` or `"light"`) |
| `opacity` | `0.96` | Widget opacity (0.50 to 1.00) |
| `always_on_top` | `true` | Pin widget on top of all windows |
| `clock_24h` | `true` | 24-hour vs 12-hour clock |
| `show_seconds` | `true` | Display seconds on digital clock |
| `auto_start` | `false` | Launch at Windows startup |
| `minimize_to_tray_on_close` | `true` | Minimize to tray when closing widget |
| `notifications_enabled` | `true` | Milestone toast notifications |

---

## 📂 Project Structure

```
office_time_widget/
├── main.py                   # Application entry point, single-instance mutex, and tray wiring
├── widget.py                 # Frameless desktop widget, clock, progress bars, and stopwatch
├── report_window.py          # Interactive monthly calendar and analytics dialog
├── excel_exporter.py         # openpyxl formatted Excel export generator
├── settings_dialog.py        # Configuration and preferences dialog
├── manual_entry_dialog.py    # Add/Edit manual session dialog
├── tray_manager.py           # System tray icon, context menu, and notifications
├── db.py                     # SQLite database manager and data layer
├── config.py                 # JSON settings and Windows Registry auto-start manager
├── theme.py                  # Dark/Light CSS stylesheets and styling constants
├── create_icon.py            # Multi-resolution .ico and .png icon generator
├── build_portable.py         # PyInstaller automated packaging script
├── OfficeTimeWidget.spec     # PyInstaller spec file
├── resources/                # App icons and graphics
├── tests/                    # Unit test suite and GUI smoke tests
│   ├── test_db_and_logic.py
│   └── test_gui_smoke.py
└── README.md                 # Documentation
```
