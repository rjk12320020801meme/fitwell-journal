"""rhythm 测试：节奏阶段判定与文案基调。"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.rhythm import DEFAULT_SETTINGS, rhythm_status, validate_settings
from app.rules import check_wording


class TestValidateSettings(unittest.TestCase):
    def test_defaults(self):
        s = validate_settings({})
        self.assertEqual(s, DEFAULT_SETTINGS)

    def test_partial_and_invalid(self):
        s = validate_settings({"bed_target": "22:30"})
        self.assertEqual(s["bed_target"], "22:30")
        self.assertEqual(s["wake_target"], "07:00")
        with self.assertRaises(ValueError):
            validate_settings({"bed_target": "25:00"})
        with self.assertRaises(ValueError):
            validate_settings({"wake_target": "7点"})


class TestRhythmStatus(unittest.TestCase):
    def test_all_phases(self):
        cases = [
            ("08:00", "morning"),    # 起床后、进食窗口前
            ("12:00", "eating"),     # 进食窗口中
            ("20:00", "wind_down"),  # 窗口收尾后、睡前 2h 前
            ("22:00", "pre_bed"),    # 睡前 2h 内
            ("23:30", "sleep"),      # 就寝后
            ("02:00", "sleep"),      # 跨午夜仍是睡眠时段
        ]
        for now, phase in cases:
            r = rhythm_status(None, now=now)
            self.assertEqual(r["phase"], phase, msg=f"now={now}")
            self.assertEqual(r["now"], now)
            self.assertTrue(r["next_time"])
            self.assertTrue(r["next_label"])

    def test_custom_targets(self):
        r = rhythm_status({"window_start": "08:00", "window_end": "17:00",
                           "bed_target": "22:00", "wake_target": "06:00"}, now="07:00")
        self.assertEqual(r["phase"], "morning")
        self.assertEqual(r["next_time"], "08:00")

    def test_gentle_wording(self):
        # 全时段文案：无诊断词、无焦虑词
        banned_extra = ("警告", "未填", "缺失", "必须", "惩罚", "失败")
        for h in range(0, 24):
            r = rhythm_status(None, now=f"{h:02d}:30")
            text = r["title"] + r["message"] + r["next_label"]
            self.assertTrue(check_wording(text), msg=f"{h}:30 文案含红线词")
            for w in banned_extra:
                self.assertNotIn(w, text, msg=f"{h}:30 文案含焦虑词 {w}")


if __name__ == "__main__":
    unittest.main()
