"""
Unit tests for DatabaseManager, Excel exporter, and time tracking calculations.
"""

import os
import sys
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
import uuid

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import ConfigManager
from db import DatabaseManager
from excel_exporter import ExcelReportExporter


class TestDatabaseAndLogic(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(__file__).parent / "test_data"
        self.test_dir.mkdir(parents=True, exist_ok=True)
        unique_id = uuid.uuid4().hex[:8]
        self.test_db_path = self.test_dir / f"test_tracker_{unique_id}.db"
        self.db = DatabaseManager(self.test_db_path)

    def tearDown(self):
        del self.db
        import gc
        gc.collect()
        if self.test_db_path.exists():
            try:
                self.test_db_path.unlink()
            except Exception:
                pass

    def test_clock_in_out(self):
        session = self.db.clock_in("Morning shift")
        self.assertIsNotNone(session)
        self.assertEqual(session["status"], "working")
        self.assertEqual(session["notes"], "Morning shift")

        active = self.db.get_active_session()
        self.assertIsNotNone(active)
        self.assertEqual(active["id"], session["id"])

        # Clock out
        completed = self.db.clock_out("Finished morning shift")
        self.assertIsNotNone(completed)
        self.assertEqual(completed["status"], "completed")
        self.assertIsNotNone(completed["clock_out"])

        active_after = self.db.get_active_session()
        self.assertIsNone(active_after)

    def test_break_tracking(self):
        session = self.db.clock_in()
        self.db.start_break()

        active = self.db.get_active_session()
        self.assertEqual(active["status"], "break")

        active_break = self.db.get_active_break(active["id"])
        self.assertIsNotNone(active_break)
        self.assertIsNone(active_break["end_time"])

        self.db.end_break()
        resumed = self.db.get_active_session()
        self.assertEqual(resumed["status"], "working")

        breaks = self.db.get_breaks_for_session(session["id"])
        self.assertEqual(len(breaks), 1)
        self.assertIsNotNone(breaks[0]["end_time"])

        self.db.clock_out()

    def test_manual_entry_and_summaries(self):
        today_str = date.today().strftime("%Y-%m-%d")
        
        # Add 5 hours session with 30 min break -> 4.5 hours net
        in_time = f"{today_str}T09:00:00"
        out_time = f"{today_str}T14:00:00"
        s_id = self.db.add_manual_session(
            session_date=today_str,
            clock_in=in_time,
            clock_out=out_time,
            break_duration_seconds=1800.0,  # 30 mins
            notes="Manual task",
        )
        self.assertTrue(s_id > 0)

        summary = self.db.get_today_summary()
        # 5 hours (18000s) - 30 min (1800s) = 16200s (4.5h)
        self.assertAlmostEqual(summary["total_work_sec"], 16200.0, delta=1.0)
        self.assertAlmostEqual(summary["total_break_sec"], 1800.0, delta=1.0)
        self.assertTrue(summary["min_reached"])  # 4.5h >= 4.0h min
        self.assertFalse(summary["target_reached"])  # 4.5h < 8.0h target

        # Add another 4 hours session -> total 8.5h
        in_time2 = f"{today_str}T15:00:00"
        out_time2 = f"{today_str}T19:00:00"
        self.db.add_manual_session(
            session_date=today_str,
            clock_in=in_time2,
            clock_out=out_time2,
            break_duration_seconds=0.0,
            notes="Evening task",
        )

        summary2 = self.db.get_today_summary()
        # 4.5h + 4.0h = 8.5h (30600s)
        self.assertAlmostEqual(summary2["total_work_sec"], 30600.0, delta=1.0)
        self.assertTrue(summary2["min_reached"])
        self.assertTrue(summary2["target_reached"])
        self.assertAlmostEqual(summary2["overtime_sec"], 1800.0, delta=1.0)  # 0.5h overtime

    def test_weekly_and_monthly_aggregations(self):
        # Insert test data across multiple days
        base_date = date(2026, 8, 10)  # A Monday
        for i in range(5):  # Mon-Fri
            day = base_date + timedelta(days=i)
            day_str = day.strftime("%Y-%m-%d")
            # 8 hours each day = 40 hours total in the week
            self.db.add_manual_session(
                session_date=day_str,
                clock_in=f"{day_str}T09:00:00",
                clock_out=f"{day_str}T17:00:00",
                break_duration_seconds=0.0,
                notes=f"Day {i+1}",
            )

        week_sum = self.db.get_week_summary(base_date)
        # 5 days * 8h = 40h = 144000 seconds
        self.assertAlmostEqual(week_sum["total_week_work_sec"], 144000.0, delta=1.0)
        self.assertTrue(week_sum["target_reached"])  # 40h >= 36h target
        self.assertAlmostEqual(week_sum["overtime_sec"], 4.0 * 3600.0, delta=1.0)

        month_sum = self.db.get_month_summary(2026, 8)
        self.assertEqual(month_sum["active_days_count"], 5)
        self.assertAlmostEqual(month_sum["total_month_work_hours"], 40.0, delta=0.1)

    def test_excel_export(self):
        base_date = date(2026, 8, 10)
        for i in range(5):
            day = base_date + timedelta(days=i)
            day_str = day.strftime("%Y-%m-%d")
            self.db.add_manual_session(
                session_date=day_str,
                clock_in=f"{day_str}T09:00:00",
                clock_out=f"{day_str}T17:30:00",
                break_duration_seconds=1800.0,
                notes=f"Work on project {i+1}",
            )

        exporter = ExcelReportExporter(self.db)
        out_excel = self.test_dir / "test_report_2026_08.xlsx"
        res_path = exporter.export_monthly_report(2026, 8, out_excel)
        self.assertTrue(res_path.exists())
        self.assertTrue(res_path.stat().st_size > 1000)

    def test_orphaned_session(self):
        yesterday = date.today() - timedelta(days=1)
        yesterday_str = yesterday.strftime("%Y-%m-%d")

        # Add manual active session from yesterday
        with self.db.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO work_sessions (
                    session_date, clock_in, clock_out, break_duration_seconds, status, notes, created_at, updated_at
                ) VALUES (?, ?, NULL, 0.0, 'working', 'PC crashed', ?, ?)
                """,
                (yesterday_str, f"{yesterday_str}T09:00:00", f"{yesterday_str}T09:00:00", f"{yesterday_str}T09:00:00"),
            )

        orphaned = self.db.get_orphaned_session()
        self.assertIsNotNone(orphaned)
        self.assertEqual(orphaned["session_date"], yesterday_str)
        self.assertEqual(orphaned["status"], "working")

    def test_custom_work_days(self):
        from config import config

        # Set work_days to Saturday (5), Sunday (6), Monday (0), Tuesday (1), Wednesday (2)
        config.set("work_days", [5, 6, 0, 1, 2], auto_save=False)

        # August 2026 has 31 days.
        # Let's verify month summary calculates expected target based on configured work days
        month_sum = self.db.get_month_summary(2026, 8)
        self.assertIn(month_sum["weekday_count"], [22, 23])  # Workdays count for Saturday-Wednesday in Aug 2026


if __name__ == "__main__":
    unittest.main()
