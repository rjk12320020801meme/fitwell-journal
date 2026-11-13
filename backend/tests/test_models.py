"""models 校验测试。"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models import ValidationError, validate_record, from_dict


class TestModels(unittest.TestCase):
    def test_meal_ok(self):
        r = validate_record("meal", {"date": "2026-11-14", "time": "08:30", "meal_type": "breakfast"})
        self.assertEqual(r["meal_type"], "breakfast")
        self.assertTrue(r["id"])
        self.assertTrue(r["created_at"])

    def test_meal_bad_type(self):
        with self.assertRaises(ValidationError):
            validate_record("meal", {"date": "2026-11-14", "time": "08:30", "meal_type": "brunch"})

    def test_bad_date_and_time(self):
        with self.assertRaises(ValidationError):
            validate_record("meal", {"date": "2026-13-40", "time": "08:30", "meal_type": "lunch"})
        with self.assertRaises(ValidationError):
            validate_record("meal", {"date": "2026-11-14", "time": "25:00", "meal_type": "lunch"})

    def test_sleep_required(self):
        with self.assertRaises(ValidationError):
            validate_record("sleep", {"date": "2026-11-14", "bed_time": "23:00"})
        r = validate_record("sleep", {"date": "2026-11-14", "bed_time": "23:00", "wake_time": "07:00",
                                      "quality": 4, "nap_min": 30})
        self.assertEqual(r["wake_time"], "07:00")

    def test_subjective_removed(self):
        # v0.1.1：主观打分项已整体移除
        with self.assertRaises(ValidationError):
            validate_record("subjective", {"date": "2026-11-14", "energy": 4, "stress": 2})

    def test_body_ranges(self):
        with self.assertRaises(ValidationError):
            validate_record("body", {"date": "2026-11-14", "weight_kg": -1})
        r = validate_record("body", {"date": "2026-11-14", "weight_kg": 70.5})
        self.assertEqual(r["weight_kg"], 70.5)

    def test_training_required(self):
        with self.assertRaises(ValidationError):
            validate_record("training", {"date": "2026-11-14", "time": "18:00", "type": "力量",
                                         "duration_min": 0})
        r = validate_record("training", {"date": "2026-11-14", "time": "18:00", "type": "力量",
                                         "duration_min": 60, "rpe": 8})
        self.assertEqual(r["duration_min"], 60)

    def test_unknown_type_and_extra_fields(self):
        with self.assertRaises(ValidationError):
            validate_record("unknown", {"date": "2026-11-14"})
        # 未知字段被忽略
        r = from_dict("meal", {"date": "2026-11-14", "time": "08:30", "meal_type": "breakfast",
                               "hack": "x"})
        self.assertNotIn("hack", r.__dict__)

    def test_roundtrip(self):
        r = validate_record("lab", {"date": "2026-11-01", "fasting_glucose": 5.2, "hba1c": 5.4})
        again = validate_record("lab", r)
        self.assertEqual(again["id"], r["id"])  # id/created_at 保留


if __name__ == "__main__":
    unittest.main()
