"""recipes 测试：数据完整性与筛选逻辑。"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.recipes import RECIPES, get_recipe, list_recipes, recommend


class TestRecipeData(unittest.TestCase):
    def test_ids_unique(self):
        ids = [r["id"] for r in RECIPES]
        self.assertEqual(len(ids), len(set(ids)))

    def test_required_fields(self):
        for r in RECIPES:
            for key in ("id", "name", "goal_tags", "meal_slots", "kcal", "protein_g",
                        "carb_g", "fat_g", "prep_min", "ingredients", "steps", "timing_tip"):
                self.assertIn(key, r, msg=f"{r.get('id')} 缺字段 {key}")
            self.assertGreaterEqual(len(r["ingredients"]), 5)
            self.assertGreaterEqual(len(r["steps"]), 3)

    def test_macros_consistent(self):
        for r in RECIPES:
            est = r["protein_g"] * 4 + r["carb_g"] * 4 + r["fat_g"] * 9
            self.assertAlmostEqual(est, r["kcal"], delta=r["kcal"] * 0.10,
                                   msg=f"{r['id']} 营养素与热量不匹配")

    def test_snack_lighter_than_meals(self):
        snacks = [r["kcal"] for r in RECIPES if r["meal_slots"] == ["snack"]]
        meals = [r["kcal"] for r in RECIPES if "snack" not in r["meal_slots"]]
        self.assertTrue(max(snacks) < min(meals))


class TestRecipeQuery(unittest.TestCase):
    def test_filter_by_goal_and_slot(self):
        for r in list_recipes(goal="cut", slot="lunch"):
            self.assertIn("cut", r["goal_tags"])
            self.assertIn("lunch", r["meal_slots"])
            self.assertNotIn("ingredients", r)  # 摘要不含做法

    def test_search(self):
        hits = list_recipes(q="鸡胸")
        self.assertGreater(len(hits), 0)
        for r in hits:
            full = get_recipe(r["id"])
            self.assertTrue("鸡胸" in full["name"] or
                            any("鸡胸" in i["item"] for i in full["ingredients"]))

    def test_get_recipe_deep_copy(self):
        r = get_recipe(RECIPES[0]["id"])
        r["name"] = "改坏了"
        self.assertNotEqual(RECIPES[0]["name"], "改坏了")
        self.assertIsNone(get_recipe("nonexistent"))

    def test_recommend_order(self):
        out = recommend(goal="cut", slot="breakfast")
        self.assertGreater(len(out), 0)
        # goal 命中（含 cut）的排在前面，maintain 兼容的在后
        tags = ["cut" in r["goal_tags"] for r in out]
        self.assertTrue(tags[0], "首选应直接命中 cut")
        self.assertEqual(tags, sorted(tags, reverse=True))


if __name__ == "__main__":
    unittest.main()
