"""规则引擎测试：代谢分/睡眠分/关联卡片/措辞红线。"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.rules import (
    BANNED_WORDS,
    check_wording,
    correlation_cards,
    grade_of,
    score_metabolic,
    score_sleep,
)
from app.trends import build_days, last_meal_to_bed, sleep_duration


def make_day(date, meals=("08:30", "12:30", "18:30"), bed="23:30", wake="07:00",
             snack_count=None, stress=None, energy=None, trained=False):
    """快速构造 day dict（绕过 build_days，直接测打分）。"""
    times = sorted(int(t[:2]) * 60 + int(t[3:]) for t in meals)
    bed_min = int(bed[:2]) * 60 + int(bed[3:])
    wake_min = int(wake[:2]) * 60 + int(wake[3:])
    gap = last_meal_to_bed(bed_min, times[-1]) if times else None
    return {
        "date": date,
        "meal_times": times,
        "meal_count": len(times),
        "snack_count": snack_count if snack_count is not None else 0,
        "window_h": (times[-1] - times[0]) / 60.0 if times else None,
        "last_meal_to_bed_min": gap,
        "eat_within_2h_before_bed": bool(gap is not None and -120 <= gap <= 120),
        "bed_min": bed_min,
        "wake_min": wake_min,
        "bed_offset_min": (bed_min - 1200) % 1440,
        "sleep_h": sleep_duration(bed_min, wake_min),
        "stress": stress,
        "energy": energy,
        "trained": trained,
        "weight_kg": None,
    }


class TestHelpers(unittest.TestCase):
    def test_cross_midnight_sleep(self):
        self.assertAlmostEqual(sleep_duration(23 * 60, 7 * 60), 8.0)

    def test_gap_wrap(self):
        # 上床 00:30、末餐 23:50（前一天）→ 间隔 40 分钟
        self.assertAlmostEqual(last_meal_to_bed(30, 23 * 60 + 50), 40)
        # 常规：末餐 21:00、上床 23:30 → 150 分钟
        self.assertAlmostEqual(last_meal_to_bed(23 * 60 + 30, 21 * 60), 150)


class TestMetabolicScore(unittest.TestCase):
    def test_ideal_pattern_high_score(self):
        days = [make_day(f"2026-11-{d:02d}") for d in range(10, 14)]
        r = score_metabolic(days)
        self.assertIsNotNone(r)
        self.assertGreaterEqual(r["score"], 85)
        self.assertEqual(r["grade"], "A")
        self.assertEqual(len(r["factors"]), 4)

    def test_late_night_pattern_low_score(self):
        days = [make_day(f"2026-11-{d:02d}", meals=("08:30", "13:00", "19:00", "23:45"),
                         bed="23:30", wake="06:00") for d in range(10, 14)]
        r = score_metabolic(days)
        self.assertLess(r["score"], 55)
        self.assertIn(r["grade"], ("C", "D"))

    def test_insufficient_days(self):
        self.assertIsNone(score_metabolic([]))
        self.assertIsNone(score_metabolic([make_day("2026-11-10")]))


class TestSleepScore(unittest.TestCase):
    def test_regular_sleep_high(self):
        days = [make_day(f"2026-11-{d:02d}", bed="23:00", wake="07:00") for d in range(9, 17)]
        r = score_sleep(days)
        self.assertGreaterEqual(r["score"], 85)
        self.assertEqual(r["grade"], "A")

    def test_irregular_sleep_lower(self):
        beds = ["22:00", "01:30", "23:00", "02:00", "22:30", "00:30", "23:30", "01:00"]
        wakes = ["06:30", "09:00", "07:00", "10:00", "06:00", "08:30", "07:30", "09:30"]
        days = [make_day(f"2026-11-{9 + i:02d}", bed=b, wake=w) for i, (b, w) in enumerate(zip(beds, wakes))]
        r = score_sleep(days)
        self.assertLess(r["score"], 85)  # 明显低于规律睡眠（≥85）
        self.assertEqual(r["grade"] in ("B", "C", "D"), True)
        # 就寝/起床波动因子被拉开（各 ±80 分钟左右 → 50 分档）
        bed_factor = next(f for f in r["factors"] if f["name"] == "就寝时刻波动")
        self.assertLessEqual(bed_factor["score"], 50)

    def test_insufficient_days(self):
        self.assertIsNone(score_sleep([make_day("2026-11-10")] * 2))
        self.assertIsNone(score_sleep([]))


class TestCorrelationCards(unittest.TestCase):
    def test_short_sleep_more_snacks(self):
        # 12 天：6 天睡 5h 且次日 2 个加餐；6 天睡 8h 且次日 0 个加餐
        days = []
        for i in range(6):
            days.append(make_day(f"2026-11-{2 * i + 1:02d}", wake="04:30", snack_count=0))   # 5h 睡眠
            days.append(make_day(f"2026-11-{2 * i + 2:02d}", snack_count=2))
        cards = correlation_cards(days)
        hit = [c for c in cards if c["title"] == "睡眠不足与加餐"]
        self.assertEqual(len(hit), 1)
        self.assertEqual(hit[0]["direction"], "up")
        self.assertTrue(check_wording(hit[0]["detail"]))

    def test_small_sample_suppressed(self):
        days = [make_day(f"2026-11-{d:02d}") for d in range(10, 13)]  # 每组不足
        self.assertEqual([c for c in correlation_cards(days) if c["title"] == "睡眠不足与加餐"], [])

    def test_stress_late_eating(self):
        days = []
        for i in range(4):
            days.append(make_day(f"2026-11-{2 * i + 1:02d}", meals=("08:30", "13:00", "23:30"),
                                 bed="23:50", stress=5))  # 压力高 + 睡前吃
            days.append(make_day(f"2026-11-{2 * i + 2:02d}", meals=("08:30", "13:00", "18:00"),
                                 bed="23:00", stress=1))
        cards = correlation_cards(days)
        hit = [c for c in cards if c["title"] == "压力与睡前进食"]
        self.assertEqual(len(hit), 1)
        self.assertEqual(hit[0]["direction"], "up")

    def test_all_cards_pass_wording_redline(self):
        days = []
        for i in range(14):
            days.append(make_day(
                f"2026-11-{i + 1:02d}",
                meals=("08:30", "13:00", "19:00", "23:30") if i % 2 else ("08:30", "12:30", "18:30"),
                wake="05:00" if i % 2 else "07:00",
                snack_count=2 if i % 2 else 0,
                stress=5 if i % 2 else 1,
                energy=2 if i % 2 else 4,
                trained=bool(i % 3)))
        for card in correlation_cards(days):
            for text in (card["title"], card["detail"]):
                for w in BANNED_WORDS:
                    self.assertNotIn(w, text)


class TestGrade(unittest.TestCase):
    def test_grades(self):
        self.assertEqual(grade_of(90), "A")
        self.assertEqual(grade_of(70), "B")
        self.assertEqual(grade_of(55), "C")
        self.assertEqual(grade_of(10), "D")
        self.assertIsNone(grade_of(None))


class TestBuildDays(unittest.TestCase):
    def test_aggregation(self):
        records = {
            "meal": [
                {"date": "2026-11-14", "time": "08:30", "meal_type": "breakfast"},
                {"date": "2026-11-14", "time": "23:30", "meal_type": "snack"},
            ],
            "sleep": [{"date": "2026-11-14", "bed_time": "23:50", "wake_time": "07:00"}],
            "subjective": [{"date": "2026-11-14", "energy": 4, "stress": 2}],
            "training": [{"date": "2026-11-14", "time": "18:00", "type": "力量", "duration_min": 60}],
            "body": [{"date": "2026-11-14", "weight_kg": 70.2}],
            "lab": [],
        }
        days = build_days(records)
        self.assertEqual(len(days), 1)
        d = days[0]
        self.assertEqual(d["meal_count"], 2)
        self.assertEqual(d["snack_count"], 1)
        self.assertTrue(d["trained"])
        self.assertTrue(d["eat_within_2h_before_bed"])  # 23:30 夜宵距 23:50 上床 20 分钟
        self.assertEqual(d["weight_kg"], 70.2)


if __name__ == "__main__":
    unittest.main()
