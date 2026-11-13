"""trends 测试：series 构建、趋势卡片、周报组装。"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.trends import build_series, trend_cards, weekly_report
from tests.test_rules import make_day


class TestSeries(unittest.TestCase):
    def test_series_shape_and_gaps(self):
        days = [make_day("2026-11-10"), make_day("2026-11-12")]
        s = build_series(days, "2026-11-10", "2026-11-13")
        self.assertEqual(s["dates"], ["2026-11-10", "2026-11-11", "2026-11-12", "2026-11-13"])
        self.assertIsNotNone(s["eating_window_h"][0])
        self.assertIsNone(s["eating_window_h"][1])  # 缺数据日为 None
        self.assertIsNone(s["eating_window_h"][3])

    def test_single_meal_day_skips_window(self):
        d = make_day("2026-11-10", meals=("12:00",))
        s = build_series([d], "2026-11-10", "2026-11-10")
        self.assertIsNone(s["eating_window_h"][0])


class TestTrendCards(unittest.TestCase):
    def test_window_shortened_card(self):
        days = []
        for i in range(1, 8):  # 前一周：12h 窗口
            days.append(make_day(f"2026-11-{i:02d}", meals=("08:00", "13:00", "20:00")))
        for i in range(8, 15):  # 近一周：9h 窗口
            days.append(make_day(f"2026-11-{i:02d}", meals=("08:00", "12:30", "17:00")))
        cards = trend_cards(days, "2026-11-08", "2026-11-14")
        hit = [c for c in cards if c["title"] == "进食窗口变化"]
        self.assertEqual(len(hit), 1)
        self.assertEqual(hit[0]["direction"], "down")
        self.assertIn("缩短", hit[0]["detail"])

    def test_no_card_on_stable_data(self):
        days = [make_day(f"2026-11-{i:02d}") for i in range(1, 15)]
        cards = trend_cards(days, "2026-11-08", "2026-11-14")
        self.assertEqual(cards, [])


class TestWeeklyReport(unittest.TestCase):
    def test_report_structure(self):
        records = {
            "meal": [], "sleep": [], "body": [], "training": [], "lab": [],
        }
        # 手工填充 14 天记录
        for i in range(1, 15):
            d = f"2026-11-{i:02d}"
            records["meal"] += [
                {"date": d, "time": "08:30", "meal_type": "breakfast"},
                {"date": d, "time": "12:30", "meal_type": "lunch"},
                {"date": d, "time": "18:30", "meal_type": "dinner"},
            ]
            records["sleep"].append({"date": d, "bed_time": "23:00", "wake_time": "07:00"})
        r = weekly_report(records, end_date="2026-11-14")
        self.assertEqual(r["period"], {"start": "2026-11-08", "end": "2026-11-14"})
        self.assertGreaterEqual(r["metabolic"]["score"], 85)
        self.assertGreaterEqual(r["sleep"]["score"], 85)
        self.assertEqual(len(r["series"]["dates"]), 7)
        self.assertIsInstance(r["cards"], list)

    def test_empty_report(self):
        records = {"meal": [], "sleep": [], "body": [], "training": [], "lab": []}
        r = weekly_report(records, end_date="2026-11-14")
        self.assertIsNone(r["metabolic"]["score"])
        self.assertIsNone(r["sleep"]["score"])
        self.assertEqual(r["cards"], [])


if __name__ == "__main__":
    unittest.main()
