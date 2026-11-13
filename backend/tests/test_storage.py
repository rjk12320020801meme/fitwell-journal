"""storage 测试：追加/查询/删除/持久化往返。"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models import ValidationError
from app.storage import JournalStore


class TestStorage(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = JournalStore(Path(self.tmp.name) / "journal.json")

    def tearDown(self):
        self.tmp.cleanup()

    def test_append_and_query(self):
        r1 = self.store.append("meal", {"date": "2026-11-14", "time": "08:30", "meal_type": "breakfast"})
        self.store.append("meal", {"date": "2026-11-13", "time": "12:00", "meal_type": "lunch"})
        self.store.append("sleep", {"date": "2026-11-14", "bed_time": "23:00", "wake_time": "07:00"})

        q = self.store.query("2026-11-14", "2026-11-14")
        self.assertEqual(len(q["meal"]), 1)
        self.assertEqual(q["meal"][0]["id"], r1["id"])
        self.assertEqual(len(q["sleep"]), 1)
        self.assertEqual(q["training"], [])

    def test_delete(self):
        r = self.store.append("meal", {"date": "2026-11-14", "time": "08:30", "meal_type": "breakfast"})
        self.assertTrue(self.store.delete("meal", r["id"]))
        self.assertFalse(self.store.delete("meal", r["id"]))
        self.assertEqual(self.store.query()["meal"], [])

    def test_invalid_record_not_saved(self):
        with self.assertRaises(ValidationError):
            self.store.append("meal", {"date": "bad", "time": "08:30", "meal_type": "breakfast"})
        self.assertEqual(self.store.query()["meal"], [])

    def test_persistence_roundtrip(self):
        self.store.append("body", {"date": "2026-11-14", "weight_kg": 70.2})
        fresh = JournalStore(self.store.path)  # 新实例重新读文件
        rows = fresh.query()["body"]
        self.assertEqual(rows[0]["weight_kg"], 70.2)


if __name__ == "__main__":
    unittest.main()
