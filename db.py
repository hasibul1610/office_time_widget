"""
SQLite Database manager and data access layer for Office Time Widget.
Handles work sessions, break logging, daily/weekly/monthly calculations, and manual adjustments.
"""

import contextlib
import shutil
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple

from config import config, get_data_dir


def get_db_path() -> Path:
    return get_data_dir() / "time_tracker.db"


class DatabaseManager:
    """Encapsulates all database operations for work tracking."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or get_db_path()
        self.init_db()

    @contextlib.contextmanager
    def connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager that ensures connections and transactions are cleanly closed."""
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def init_db(self) -> None:
        """Initializes database schema and indexes."""
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS work_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_date TEXT NOT NULL,
                    clock_in TEXT NOT NULL,
                    clock_out TEXT,
                    break_duration_seconds REAL DEFAULT 0.0,
                    status TEXT NOT NULL CHECK(status IN ('working', 'break', 'completed')),
                    notes TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS break_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    duration_seconds REAL DEFAULT 0.0,
                    FOREIGN KEY (session_id) REFERENCES work_sessions(id) ON DELETE CASCADE
                );
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_sessions_date ON work_sessions(session_date);
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_sessions_status ON work_sessions(status);
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_break_session ON break_logs(session_id);
                """
            )

    # --- Session Controls ---

    def clock_in(self, notes: str = "") -> Dict[str, Any]:
        """Starts a new active work session. If one is already active, returns it."""
        active = self.get_active_session()
        if active:
            return active

        now = datetime.now()
        now_iso = now.isoformat(timespec="seconds")
        today_str = now.strftime("%Y-%m-%d")

        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO work_sessions (
                    session_date, clock_in, clock_out, break_duration_seconds, status, notes, created_at, updated_at
                ) VALUES (?, ?, NULL, 0.0, 'working', ?, ?, ?)
                """,
                (today_str, now_iso, notes, now_iso, now_iso),
            )
            session_id = cursor.lastrowid

        return self.get_session_by_id(session_id)

    def clock_out(self, notes: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Ends the currently active session (completing break if active)."""
        active = self.get_active_session()
        if not active:
            return None

        now = datetime.now()
        now_iso = now.isoformat(timespec="seconds")
        session_id = active["id"]

        with self.connection() as conn:
            cursor = conn.cursor()

            # If currently on break, close open break log first
            if active["status"] == "break":
                active_break = self.get_active_break(session_id)
                if active_break:
                    b_start = datetime.fromisoformat(active_break["start_time"])
                    b_duration = max(0.0, (now - b_start).total_seconds())
                    cursor.execute(
                        """
                        UPDATE break_logs 
                        SET end_time = ?, duration_seconds = ?
                        WHERE id = ?
                        """,
                        (now_iso, b_duration, active_break["id"]),
                    )
                    # Add to session break total
                    cursor.execute(
                        """
                        UPDATE work_sessions
                        SET break_duration_seconds = break_duration_seconds + ?
                        WHERE id = ?
                        """,
                        (b_duration, session_id),
                    )

            # Update session to completed
            if notes is not None:
                cursor.execute(
                    """
                    UPDATE work_sessions 
                    SET clock_out = ?, status = 'completed', notes = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (now_iso, notes, now_iso, session_id),
                )
            else:
                cursor.execute(
                    """
                    UPDATE work_sessions 
                    SET clock_out = ?, status = 'completed', updated_at = ?
                    WHERE id = ?
                    """,
                    (now_iso, now_iso, session_id),
                )

        return self.get_session_by_id(session_id)

    def start_break(self) -> Optional[Dict[str, Any]]:
        """Puts active session on break."""
        active = self.get_active_session()
        if not active or active["status"] == "break":
            return active

        now = datetime.now()
        now_iso = now.isoformat(timespec="seconds")
        session_id = active["id"]

        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO break_logs (session_id, start_time, end_time, duration_seconds)
                VALUES (?, ?, NULL, 0.0)
                """,
                (session_id, now_iso),
            )
            cursor.execute(
                """
                UPDATE work_sessions
                SET status = 'break', updated_at = ?
                WHERE id = ?
                """,
                (now_iso, session_id),
            )

        return self.get_session_by_id(session_id)

    def end_break(self) -> Optional[Dict[str, Any]]:
        """Resumes active session from break."""
        active = self.get_active_session()
        if not active or active["status"] != "break":
            return active

        now = datetime.now()
        now_iso = now.isoformat(timespec="seconds")
        session_id = active["id"]

        with self.connection() as conn:
            cursor = conn.cursor()
            active_break = self.get_active_break(session_id)
            if active_break:
                b_start = datetime.fromisoformat(active_break["start_time"])
                b_duration = max(0.0, (now - b_start).total_seconds())
                cursor.execute(
                    """
                    UPDATE break_logs 
                    SET end_time = ?, duration_seconds = ?
                    WHERE id = ?
                    """,
                    (now_iso, b_duration, active_break["id"]),
                )
                cursor.execute(
                    """
                    UPDATE work_sessions
                    SET status = 'working', break_duration_seconds = break_duration_seconds + ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (b_duration, now_iso, session_id),
                )
            else:
                cursor.execute(
                    """
                    UPDATE work_sessions
                    SET status = 'working', updated_at = ?
                    WHERE id = ?
                    """,
                    (now_iso, session_id),
                )

        return self.get_session_by_id(session_id)

    # --- Query Helpers ---

    def get_session_by_id(self, session_id: int) -> Optional[Dict[str, Any]]:
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM work_sessions WHERE id = ?", (session_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_active_session(self) -> Optional[Dict[str, Any]]:
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM work_sessions 
                WHERE status IN ('working', 'break') 
                ORDER BY id DESC LIMIT 1
                """
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_orphaned_session(self) -> Optional[Dict[str, Any]]:
        """
        Returns any active session ('working' or 'break') from a date prior to today.
        Used to detect unexpected shutdowns or crashed sessions from previous days.
        """
        today_str = datetime.now().strftime("%Y-%m-%d")
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM work_sessions 
                WHERE status IN ('working', 'break') AND session_date < ? 
                ORDER BY id DESC LIMIT 1
                """,
                (today_str,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_active_break(self, session_id: int) -> Optional[Dict[str, Any]]:
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM break_logs 
                WHERE session_id = ? AND end_time IS NULL 
                ORDER BY id DESC LIMIT 1
                """,
                (session_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_breaks_for_session(self, session_id: int) -> List[Dict[str, Any]]:
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM break_logs WHERE session_id = ? ORDER BY start_time ASC",
                (session_id,),
            )
            return [dict(r) for r in cursor.fetchall()]

    def get_sessions_by_date(self, session_date: str) -> List[Dict[str, Any]]:
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM work_sessions 
                WHERE session_date = ? 
                ORDER BY clock_in ASC
                """,
                (session_date,),
            )
            return [dict(r) for r in cursor.fetchall()]

    # --- Time & Aggregation Logic ---

    @staticmethod
    def calculate_session_duration(
        session: Dict[str, Any],
        current_break: Optional[Dict[str, Any]] = None,
        now: Optional[datetime] = None,
    ) -> Tuple[float, float]:
        """
        Calculates (work_seconds, total_break_seconds) for a session dict.
        Accurately accounts for live active sessions and in-progress breaks.
        """
        if now is None:
            now = datetime.now()

        try:
            clock_in = datetime.fromisoformat(session["clock_in"])
        except Exception:
            return 0.0, 0.0

        if session.get("clock_out"):
            try:
                clock_out = datetime.fromisoformat(session["clock_out"])
            except Exception:
                clock_out = now
        else:
            clock_out = now

        total_elapsed = max(0.0, (clock_out - clock_in).total_seconds())
        break_sec = float(session.get("break_duration_seconds", 0.0) or 0.0)

        # If currently in break, add ongoing break time
        if session["status"] == "break" and current_break and current_break.get("start_time"):
            try:
                b_start = datetime.fromisoformat(current_break["start_time"])
                ongoing_break = max(0.0, (now - b_start).total_seconds())
                break_sec += ongoing_break
            except Exception:
                pass

        work_sec = max(0.0, total_elapsed - break_sec)
        return work_sec, break_sec

    def get_today_summary(self, target_date: Optional[date] = None) -> Dict[str, Any]:
        """Returns comprehensive summary for today (or specified date)."""
        now = datetime.now()
        d = target_date or now.date()
        date_str = d.strftime("%Y-%m-%d")

        sessions = self.get_sessions_by_date(date_str)
        active = self.get_active_session()
        active_break = self.get_active_break(active["id"]) if active else None

        total_work_sec = 0.0
        total_break_sec = 0.0
        current_session_work_sec = 0.0
        current_break_sec = 0.0

        for s in sessions:
            if active and s["id"] == active["id"]:
                w_sec, b_sec = self.calculate_session_duration(s, active_break, now)
                current_session_work_sec = w_sec
                if active["status"] == "break" and active_break:
                    try:
                        b_start = datetime.fromisoformat(active_break["start_time"])
                        current_break_sec = max(0.0, (now - b_start).total_seconds())
                    except Exception:
                        pass
            else:
                w_sec, b_sec = self.calculate_session_duration(s, None, now)

            total_work_sec += w_sec
            total_break_sec += b_sec

        current_status = active["status"] if active and active["session_date"] == date_str else "idle"

        daily_min_hours = float(config.get("daily_min_hours", 4.0))
        daily_target_hours = float(config.get("daily_target_hours", 8.0))

        min_sec = daily_min_hours * 3600.0
        target_sec = daily_target_hours * 3600.0

        min_progress = min(1.0, total_work_sec / min_sec) if min_sec > 0 else 1.0
        target_progress = min(1.0, total_work_sec / target_sec) if target_sec > 0 else 1.0
        overtime_sec = max(0.0, total_work_sec - target_sec)

        return {
            "date": date_str,
            "status": current_status,
            "active_session": active if active and active["session_date"] == date_str else None,
            "current_session_work_sec": current_session_work_sec,
            "current_break_sec": current_break_sec,
            "total_work_sec": total_work_sec,
            "total_break_sec": total_break_sec,
            "sessions_count": len(sessions),
            "sessions": sessions,
            "min_sec": min_sec,
            "target_sec": target_sec,
            "min_progress": min_progress,
            "target_progress": target_progress,
            "min_reached": total_work_sec >= min_sec,
            "target_reached": total_work_sec >= target_sec,
            "overtime_sec": overtime_sec,
            "remaining_to_min_sec": max(0.0, min_sec - total_work_sec),
            "remaining_to_target_sec": max(0.0, target_sec - total_work_sec),
        }

    def get_week_summary(self, ref_date: Optional[date] = None) -> Dict[str, Any]:
        """Calculates statistics for the Monday-Sunday week containing ref_date."""
        now = datetime.now()
        d = ref_date or now.date()
        start_of_week = d - timedelta(days=d.weekday())  # Monday
        end_of_week = start_of_week + timedelta(days=6)  # Sunday

        weekly_target_hours = float(config.get("weekly_target_hours", 36.0))
        weekly_target_sec = weekly_target_hours * 3600.0

        daily_stats = []
        total_week_work_sec = 0.0
        total_week_break_sec = 0.0

        curr = start_of_week
        while curr <= end_of_week:
            curr_str = curr.strftime("%Y-%m-%d")
            day_sum = self.get_today_summary(curr)
            daily_stats.append({
                "date": curr_str,
                "day_name": curr.strftime("%a"),
                "is_today": curr == now.date(),
                "is_past": curr < now.date(),
                "work_sec": day_sum["total_work_sec"],
                "break_sec": day_sum["total_break_sec"],
                "min_reached": day_sum["min_reached"],
                "target_reached": day_sum["target_reached"],
            })
            total_week_work_sec += day_sum["total_work_sec"]
            total_week_break_sec += day_sum["total_break_sec"]
            curr += timedelta(days=1)

        week_progress = (
            min(1.0, total_week_work_sec / weekly_target_sec) if weekly_target_sec > 0 else 1.0
        )
        remaining_sec = max(0.0, weekly_target_sec - total_week_work_sec)
        overtime_sec = max(0.0, total_week_work_sec - weekly_target_sec)

        return {
            "start_date": start_of_week.strftime("%Y-%m-%d"),
            "end_date": end_of_week.strftime("%Y-%m-%d"),
            "weekly_target_sec": weekly_target_sec,
            "weekly_target_hours": weekly_target_hours,
            "total_week_work_sec": total_week_work_sec,
            "total_week_break_sec": total_week_break_sec,
            "week_progress": week_progress,
            "remaining_sec": remaining_sec,
            "overtime_sec": overtime_sec,
            "target_reached": total_week_work_sec >= weekly_target_sec,
            "days": daily_stats,
        }

    def get_month_summary(self, year: int, month: int) -> Dict[str, Any]:
        """Calculates month-level statistics, daily aggregates, and week breakdown."""
        start_date = date(year, month, 1)
        if month == 12:
            next_month = date(year + 1, 1, 1)
        else:
            next_month = date(year, month + 1, 1)
        days_in_month = (next_month - start_date).days

        daily_data: Dict[str, Dict[str, Any]] = {}
        total_month_work_sec = 0.0
        total_month_break_sec = 0.0
        active_days_count = 0
        weekday_count = 0

        daily_target_hours = float(config.get("daily_target_hours", 8.0))

        for day in range(1, days_in_month + 1):
            curr_date = date(year, month, day)
            curr_str = curr_date.strftime("%Y-%m-%d")
            day_sum = self.get_today_summary(curr_date)

            work_sec = day_sum["total_work_sec"]
            break_sec = day_sum["total_break_sec"]

            work_days = config.get("work_days", [5, 6, 0, 1, 2])
            if curr_date.weekday() in work_days:
                weekday_count += 1

            if work_sec > 60.0:  # Active if worked at least 1 min
                active_days_count += 1

            total_month_work_sec += work_sec
            total_month_break_sec += break_sec

            daily_data[curr_str] = {
                "date": curr_str,
                "day": day,
                "day_name": curr_date.strftime("%a"),
                "weekday": curr_date.weekday(),
                "work_sec": work_sec,
                "break_sec": break_sec,
                "work_hours": work_sec / 3600.0,
                "sessions_count": day_sum["sessions_count"],
                "sessions": day_sum["sessions"],
                "min_reached": day_sum["min_reached"],
                "target_reached": day_sum["target_reached"],
            }

        expected_target_sec = weekday_count * daily_target_hours * 3600.0
        balance_sec = total_month_work_sec - expected_target_sec

        # Group into weeks for monthly report
        weeks = []
        curr = start_date
        week_num = 1
        while curr < next_month:
            w_start = curr - timedelta(days=curr.weekday())
            w_end = w_start + timedelta(days=6)

            # Clamp to month bounds for reporting
            clamped_start = max(start_date, w_start)
            clamped_end = min(date(year, month, days_in_month), w_end)

            w_sum = self.get_week_summary(curr)
            weeks.append({
                "week_num": week_num,
                "range_label": f"{clamped_start.strftime('%b %d')} - {clamped_end.strftime('%b %d')}",
                "work_sec": w_sum["total_week_work_sec"],
                "work_hours": w_sum["total_week_work_sec"] / 3600.0,
                "target_hours": w_sum["weekly_target_hours"],
                "target_reached": w_sum["target_reached"],
            })
            week_num += 1
            curr = w_end + timedelta(days=1)

        return {
            "year": year,
            "month": month,
            "month_name": start_date.strftime("%B"),
            "days_in_month": days_in_month,
            "weekday_count": weekday_count,
            "active_days_count": active_days_count,
            "total_month_work_sec": total_month_work_sec,
            "total_month_work_hours": total_month_work_sec / 3600.0,
            "total_month_break_sec": total_month_break_sec,
            "expected_target_sec": expected_target_sec,
            "expected_target_hours": expected_target_sec / 3600.0,
            "balance_sec": balance_sec,
            "balance_hours": balance_sec / 3600.0,
            "avg_hours_per_active_day": (
                (total_month_work_sec / 3600.0 / active_days_count) if active_days_count > 0 else 0.0
            ),
            "daily_data": daily_data,
            "weeks": weeks,
        }

    # --- Manual Session CRUD ---

    def add_manual_session(
        self,
        session_date: str,
        clock_in: str,
        clock_out: str,
        break_duration_seconds: float = 0.0,
        notes: str = "",
    ) -> int:
        now_iso = datetime.now().isoformat(timespec="seconds")
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO work_sessions (
                    session_date, clock_in, clock_out, break_duration_seconds, status, notes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, 'completed', ?, ?, ?)
                """,
                (
                    session_date,
                    clock_in,
                    clock_out,
                    float(break_duration_seconds),
                    notes,
                    now_iso,
                    now_iso,
                ),
            )
            return cursor.lastrowid

    def update_session(
        self,
        session_id: int,
        session_date: str,
        clock_in: str,
        clock_out: Optional[str],
        break_duration_seconds: float,
        notes: str,
    ) -> bool:
        now_iso = datetime.now().isoformat(timespec="seconds")
        status = "completed" if clock_out else "working"
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE work_sessions 
                SET session_date = ?, clock_in = ?, clock_out = ?, break_duration_seconds = ?, 
                    status = ?, notes = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    session_date,
                    clock_in,
                    clock_out,
                    float(break_duration_seconds),
                    status,
                    notes,
                    now_iso,
                    session_id,
                ),
            )
            return cursor.rowcount > 0

    def delete_session(self, session_id: int) -> bool:
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM work_sessions WHERE id = ?", (session_id,))
            return cursor.rowcount > 0

    def clear_all_data(self) -> None:
        """Clears all records from tables."""
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM break_logs")
            cursor.execute("DELETE FROM work_sessions")

    # --- Backup & Maintenance ---

    def backup_db(self, backup_dir: Path) -> Path:
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = backup_dir / f"time_tracker_backup_{timestamp}.db"
        shutil.copy2(self.db_path, target)
        return target


# Global singleton instance
db = DatabaseManager()
