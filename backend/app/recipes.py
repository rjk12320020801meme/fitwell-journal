"""fitwell-journal 食谱数据模块（纯标准库，无第三方依赖）。

数据结构
--------
RECIPES: list[dict]，每道食谱为一个 dict，字段如下：

    id           : str  英文短横线 slug，全局唯一
    name         : str  中文菜名
    goal_tags    : list[str]  适用目标子集，取值 "cut" / "maintain" / "gain"
    meal_slots   : list[str]  适用餐段子集，取值 "breakfast" / "lunch" / "dinner" / "snack"
    kcal         : int   每份热量（kcal）
    protein_g    : float 每份蛋白质（g）
    carb_g       : float 每份碳水（g）
    fat_g        : float 每份脂肪（g）
    prep_min     : int   准备/烹饪耗时（分钟）
    ingredients  : list[dict]  6-10 项，每项 {"item": 中文食材, "amount": 中文用量}
    steps        : list[str]   4-7 步中文做法，每步一个可执行动作，面向厨房新手
    timing_tip   : str  食用时机建议

营养数字自洽：kcal ≈ 4*protein_g + 4*carb_g + 9*fat_g（±10% 以内）。
正餐每份约 400-650 kcal，加餐每份约 150-350 kcal。

对外接口
--------
list_recipes(goal=None, slot=None, q=None) -> list[dict]
    返回食谱摘要列表（不含 ingredients/steps）。goal/slot 按标签包含过滤；
    q 对 name 与食材 item 做不区分大小写的包含匹配。

get_recipe(recipe_id: str) -> dict | None
    返回完整食谱（含 ingredients/steps）的深拷贝；未找到返回 None。

recommend(goal=None, slot=None, q=None, limit=20) -> list[dict]
    与 list_recipes 同族的推荐接口：goal 命中排在"仅 maintain 兼容"之前，
    同档内按 prep_min 升序，返回前 limit 条摘要。

所有对外返回均为拷贝，调用方修改不会污染模块内的 RECIPES 数据。
"""

from __future__ import annotations

import copy

__all__ = ["RECIPES", "list_recipes", "get_recipe", "recommend"]

_GOALS = frozenset({"cut", "maintain", "gain"})
_SLOTS = frozenset({"breakfast", "lunch", "dinner", "snack"})

_SUMMARY_KEYS = (
    "id",
    "name",
    "goal_tags",
    "meal_slots",
    "kcal",
    "protein_g",
    "carb_g",
    "fat_g",
    "prep_min",
    "timing_tip",
)

RECIPES: list[dict] = [
    {
        "id": "high-protein-oat-bowl",
        "name": "高蛋白早餐燕麦碗",
        "goal_tags": ["cut", "maintain"],
        "meal_slots": ["breakfast"],
        "kcal": 505,
        "protein_g": 36.0,
        "carb_g": 63.0,
        "fat_g": 12.0,
        "prep_min": 10,
        "ingredients": [
            {"item": "燕麦片", "amount": "50g"},
            {"item": "低脂牛奶", "amount": "200ml"},
            {"item": "乳清蛋白粉", "amount": "25g"},
            {"item": "香蕉", "amount": "半根（约50g）"},
            {"item": "蓝莓", "amount": "30g"},
            {"item": "无糖花生酱", "amount": "10g"},
            {"item": "肉桂粉", "amount": "少许"},
        ],
        "steps": [
            "燕麦片 50g 倒入碗中，加入低脂牛奶 200ml，微波高火加热 2 分钟。",
            "取出搅拌至浓稠，静置 1 分钟让燕麦吸饱牛奶。",
            "乳清蛋白粉 25g 加 30ml 温水调成糊状，拌入燕麦碗。",
            "香蕉半根切片、蓝莓 30g 洗净，铺在燕麦上。",
            "淋上无糖花生酱 10g，撒少许肉桂粉即可。",
        ],
        "timing_tip": "适合起床后 1 小时内食用；训练前 1 小时吃能提供稳定能量。",
    },
    {
        "id": "chicken-salad-wrap",
        "name": "鸡胸肉沙拉卷",
        "goal_tags": ["cut", "maintain"],
        "meal_slots": ["lunch"],
        "kcal": 475,
        "protein_g": 48.0,
        "carb_g": 38.0,
        "fat_g": 14.0,
        "prep_min": 15,
        "ingredients": [
            {"item": "全麦卷饼", "amount": "1 张（约60g）"},
            {"item": "鸡胸肉", "amount": "120g"},
            {"item": "生菜", "amount": "50g"},
            {"item": "番茄", "amount": "80g"},
            {"item": "黄瓜", "amount": "60g"},
            {"item": "彩椒", "amount": "50g"},
            {"item": "无糖希腊酸奶", "amount": "30g"},
            {"item": "橄榄油", "amount": "5g"},
            {"item": "黑胡椒", "amount": "1g"},
        ],
        "steps": [
            "鸡胸肉 120g 横切成薄片，撒盐和黑胡椒腌 5 分钟。",
            "平底锅刷橄榄油 5g，中火两面各煎 3 分钟至全熟，取出切条。",
            "生菜、番茄、黄瓜、彩椒洗净，全部切成细条。",
            "无糖希腊酸奶 30g 加黑胡椒拌匀，调成抹酱。",
            "全麦卷饼铺平，抹上酸奶酱，放蔬菜条和鸡肉条，卷紧后对半切开。",
        ],
        "timing_tip": "适合午餐，尤其适合训练后 1 小时内补充蛋白质。",
    },
    {
        "id": "tomato-beef-pasta",
        "name": "番茄牛肉意面",
        "goal_tags": ["maintain", "gain"],
        "meal_slots": ["lunch", "dinner"],
        "kcal": 610,
        "protein_g": 39.0,
        "carb_g": 68.0,
        "fat_g": 20.0,
        "prep_min": 25,
        "ingredients": [
            {"item": "全麦意面", "amount": "80g"},
            {"item": "牛里脊肉末", "amount": "120g"},
            {"item": "番茄丁", "amount": "150g"},
            {"item": "洋葱", "amount": "50g"},
            {"item": "胡萝卜", "amount": "40g"},
            {"item": "橄榄油", "amount": "8g"},
            {"item": "帕玛森芝士", "amount": "5g"},
            {"item": "盐", "amount": "1g"},
            {"item": "黑胡椒", "amount": "1g"},
        ],
        "steps": [
            "烧一锅水，水开后加盐，放入全麦意面 80g 煮 9 分钟至有嚼劲。",
            "另起锅倒橄榄油 8g，中火炒香洋葱丁和胡萝卜丁 3 分钟。",
            "放入牛里脊肉末 120g，炒散至完全变色。",
            "倒入番茄丁 150g，小火煮 10 分钟至浓稠，用盐和黑胡椒调味。",
            "捞出意面放入酱汁中拌匀，装盘后擦上帕玛森芝士 5g。",
        ],
        "timing_tip": "适合训练日晚餐，碳水充足，帮助训练后糖原恢复。",
    },
    {
        "id": "salmon-brown-rice-bowl",
        "name": "三文鱼糙米饭",
        "goal_tags": ["maintain", "gain"],
        "meal_slots": ["lunch", "dinner"],
        "kcal": 535,
        "protein_g": 35.0,
        "carb_g": 47.0,
        "fat_g": 23.0,
        "prep_min": 20,
        "ingredients": [
            {"item": "三文鱼", "amount": "120g"},
            {"item": "糙米饭", "amount": "150g"},
            {"item": "西兰花", "amount": "100g"},
            {"item": "芦笋", "amount": "60g"},
            {"item": "牛油果", "amount": "30g"},
            {"item": "生抽", "amount": "8ml"},
            {"item": "白芝麻", "amount": "3g"},
            {"item": "柠檬汁", "amount": "10ml"},
        ],
        "steps": [
            "三文鱼 120g 用生抽 8ml 和柠檬汁 10ml 腌 10 分钟。",
            "平底锅不放油，中火将三文鱼带皮面朝下煎 4 分钟，翻面再煎 3 分钟。",
            "西兰花 100g、芦笋 60g 洗净切段，沸水焯 2 分钟捞出。",
            "糙米饭 150g 装碗，摆上三文鱼、焯好的蔬菜和牛油果 30g 切片。",
            "撒上白芝麻 3g 即可。",
        ],
        "timing_tip": "适合晚餐，富含 Omega-3；减脂期可把糙米饭减到 100g。",
    },
    {
        "id": "tofu-chicken-veg-pot",
        "name": "豆腐鸡胸蔬菜煲",
        "goal_tags": ["cut", "maintain"],
        "meal_slots": ["dinner"],
        "kcal": 448,
        "protein_g": 44.0,
        "carb_g": 32.0,
        "fat_g": 16.0,
        "prep_min": 30,
        "ingredients": [
            {"item": "鸡胸肉", "amount": "100g"},
            {"item": "北豆腐", "amount": "150g"},
            {"item": "娃娃菜", "amount": "150g"},
            {"item": "香菇", "amount": "80g"},
            {"item": "干木耳", "amount": "5g"},
            {"item": "红薯", "amount": "80g"},
            {"item": "姜", "amount": "5g"},
            {"item": "蒜", "amount": "2 瓣"},
            {"item": "生抽", "amount": "10ml"},
            {"item": "芝麻油", "amount": "5g"},
        ],
        "steps": [
            "干木耳 5g 用温水泡发 20 分钟，洗净撕成小朵。",
            "鸡胸肉 100g 切块，北豆腐 150g 切方块，红薯 80g 切滚刀块。",
            "锅中放芝麻油 5g，爆香姜片和蒜瓣，下鸡肉块炒至变色。",
            "加入红薯、香菇 80g、木耳和生抽 10ml，倒 400ml 热水，中小火煮 10 分钟。",
            "放入豆腐和娃娃菜 150g，再煮 5 分钟至软烂即可。",
        ],
        "timing_tip": "适合晚餐，热量密度低、饱腹感强，减脂期也不容易饿。",
    },
    {
        "id": "greek-yogurt-parfait",
        "name": "希腊酸奶加餐杯",
        "goal_tags": ["cut", "maintain", "gain"],
        "meal_slots": ["snack"],
        "kcal": 270,
        "protein_g": 20.0,
        "carb_g": 32.0,
        "fat_g": 7.0,
        "prep_min": 5,
        "ingredients": [
            {"item": "无糖希腊酸奶", "amount": "150g"},
            {"item": "蓝莓", "amount": "40g"},
            {"item": "燕麦片", "amount": "15g"},
            {"item": "奇亚籽", "amount": "5g"},
            {"item": "蜂蜜", "amount": "8g"},
            {"item": "杏仁片", "amount": "5g"},
        ],
        "steps": [
            "燕麦片 15g 干锅小火烘 2 分钟至微黄，取出放凉。",
            "玻璃杯底层铺入希腊酸奶 150g 的一半。",
            "撒上烘好的燕麦片和奇亚籽 5g，再铺另一半酸奶。",
            "放蓝莓 40g 和杏仁片 5g，淋蜂蜜 8g，冷藏 10 分钟后食用。",
        ],
        "timing_tip": "适合下午加餐或训练前 1 小时，缓解正餐之间的饥饿。",
    },
    {
        "id": "veggie-egg-pancake",
        "name": "鸡蛋蔬菜饼",
        "goal_tags": ["maintain", "gain"],
        "meal_slots": ["breakfast"],
        "kcal": 420,
        "protein_g": 28.0,
        "carb_g": 41.0,
        "fat_g": 16.0,
        "prep_min": 15,
        "ingredients": [
            {"item": "鸡蛋", "amount": "2 个（约100g）"},
            {"item": "蛋清", "amount": "2 个（约66g）"},
            {"item": "全麦面粉", "amount": "30g"},
            {"item": "土豆", "amount": "80g"},
            {"item": "胡萝卜", "amount": "40g"},
            {"item": "菠菜", "amount": "50g"},
            {"item": "小葱", "amount": "10g"},
            {"item": "橄榄油", "amount": "5g"},
            {"item": "盐", "amount": "1g"},
        ],
        "steps": [
            "土豆 80g、胡萝卜 40g 去皮擦丝，菠菜 50g 切碎，小葱切葱花。",
            "鸡蛋 2 个加蛋清 2 个打散，加入全麦面粉 30g 和 30ml 清水搅成面糊。",
            "把土豆丝、胡萝卜丝、菠菜碎、葱花和盐 1g 倒入面糊拌匀。",
            "平底锅刷橄榄油 5g，中小火倒入面糊摊平，煎 4 分钟至底面金黄。",
            "翻面再煎 3 分钟，切块装盘即可。",
        ],
        "timing_tip": "适合训练日早餐，碳水充足，能支撑上午的训练。",
    },
    {
        "id": "shrimp-egg-rice-bowl",
        "name": "虾仁炒蛋盖饭",
        "goal_tags": ["maintain", "gain"],
        "meal_slots": ["lunch"],
        "kcal": 550,
        "protein_g": 39.0,
        "carb_g": 52.0,
        "fat_g": 19.0,
        "prep_min": 15,
        "ingredients": [
            {"item": "虾仁", "amount": "120g"},
            {"item": "鸡蛋", "amount": "2 个（约100g）"},
            {"item": "米饭", "amount": "180g"},
            {"item": "青豆", "amount": "30g"},
            {"item": "小葱", "amount": "10g"},
            {"item": "生抽", "amount": "8ml"},
            {"item": "食用油", "amount": "7g"},
            {"item": "盐", "amount": "1g"},
        ],
        "steps": [
            "虾仁 120g 解冻擦干，加盐 1g 抓匀；鸡蛋 2 个打散；青豆 30g 焯水 1 分钟。",
            "锅中放食用油 4g，倒入蛋液炒至半凝固，盛出备用。",
            "补 3g 油，大火下虾仁炒至变红卷曲。",
            "倒入青豆和炒蛋，加生抽 8ml 快炒 30 秒。",
            "米饭 180g 装碗，盖上虾仁炒蛋，撒葱花即可。",
        ],
        "timing_tip": "适合训练后 1 小时内的午餐，快炒做法 15 分钟就能上桌。",
    },
    {
        "id": "teriyaki-chicken-thigh-rice",
        "name": "照烧鸡腿糙米饭（去皮）",
        "goal_tags": ["maintain", "gain"],
        "meal_slots": ["lunch", "dinner"],
        "kcal": 530,
        "protein_g": 35.0,
        "carb_g": 66.0,
        "fat_g": 14.0,
        "prep_min": 25,
        "ingredients": [
            {"item": "去皮鸡腿肉", "amount": "150g"},
            {"item": "糙米饭", "amount": "180g"},
            {"item": "西兰花", "amount": "100g"},
            {"item": "胡萝卜", "amount": "50g"},
            {"item": "生抽", "amount": "10ml"},
            {"item": "蜂蜜", "amount": "10g"},
            {"item": "味淋", "amount": "10ml"},
            {"item": "姜", "amount": "5g"},
            {"item": "食用油", "amount": "5g"},
        ],
        "steps": [
            "鸡腿肉 150g 用刀背拍松，加生抽 10ml、蜂蜜 10g、味淋 10ml 和姜丝腌 15 分钟。",
            "西兰花 100g 掰小朵、胡萝卜 50g 切片，沸水焯 2 分钟捞出。",
            "平底锅放食用油 5g，中火将鸡腿肉两面各煎 4 分钟至金黄。",
            "倒入腌汁，小火收至浓稠并裹匀鸡肉，取出切条。",
            "糙米饭 180g 装碗，摆上鸡腿肉和焯好的蔬菜即可。",
        ],
        "timing_tip": "适合增肌期午餐；减脂期把糙米饭减到 120g、蜂蜜减半。",
    },
    {
        "id": "tuna-wholewheat-sandwich",
        "name": "金枪鱼全麦三明治",
        "goal_tags": ["cut", "maintain"],
        "meal_slots": ["breakfast", "lunch"],
        "kcal": 430,
        "protein_g": 43.0,
        "carb_g": 37.0,
        "fat_g": 12.0,
        "prep_min": 10,
        "ingredients": [
            {"item": "全麦吐司", "amount": "2 片（约70g）"},
            {"item": "水浸金枪鱼罐头", "amount": "100g"},
            {"item": "无糖希腊酸奶", "amount": "20g"},
            {"item": "生菜", "amount": "30g"},
            {"item": "番茄", "amount": "60g"},
            {"item": "黄瓜", "amount": "40g"},
            {"item": "牛油果", "amount": "20g"},
            {"item": "鸡蛋", "amount": "1 个"},
            {"item": "黑胡椒", "amount": "1g"},
        ],
        "steps": [
            "鸡蛋 1 个冷水下锅煮 8 分钟，捞出过凉水剥壳切片。",
            "金枪鱼罐头 100g 沥干水分，与希腊酸奶 20g、黑胡椒 1g 拌匀成沙拉。",
            "番茄 60g、黄瓜 40g 洗净切薄片，牛油果 20g 切片。",
            "吐司烤至微脆，铺生菜，抹金枪鱼沙拉，码上蛋片、番茄、黄瓜和牛油果。",
            "盖上另一片吐司，压紧后对角切开即可。",
        ],
        "timing_tip": "可提前一晚备好食材，适合当早餐或外带午餐便当。",
    },
    {
        "id": "sweet-potato-chicken-bento",
        "name": "红薯鸡胸便当",
        "goal_tags": ["cut", "maintain"],
        "meal_slots": ["lunch"],
        "kcal": 480,
        "protein_g": 44.0,
        "carb_g": 52.0,
        "fat_g": 11.0,
        "prep_min": 25,
        "ingredients": [
            {"item": "鸡胸肉", "amount": "150g"},
            {"item": "红薯", "amount": "200g"},
            {"item": "西兰花", "amount": "100g"},
            {"item": "彩椒", "amount": "80g"},
            {"item": "橄榄油", "amount": "6g"},
            {"item": "生抽", "amount": "8ml"},
            {"item": "蒜", "amount": "2 瓣"},
            {"item": "黑胡椒", "amount": "1g"},
        ],
        "steps": [
            "红薯 200g 去皮切 2cm 方块，铺在烤盘上，表面刷橄榄油 3g。",
            "烤箱 200℃ 烤 20 分钟至边缘焦糖化。",
            "鸡胸肉 150g 横切厚片，用生抽 8ml、蒜末和黑胡椒 1g 腌 10 分钟。",
            "锅中放橄榄油 3g，中火煎鸡胸肉两面各 4 分钟至全熟。",
            "西兰花 100g、彩椒 80g 切块焯水 2 分钟，与红薯、鸡肉一起装入便当盒。",
        ],
        "timing_tip": "适合备餐日一次做两份，冷藏后第二天带饭复热即可。",
    },
    {
        "id": "protein-shake",
        "name": "蛋白奶昔加餐",
        "goal_tags": ["cut", "maintain", "gain"],
        "meal_slots": ["snack"],
        "kcal": 320,
        "protein_g": 31.0,
        "carb_g": 32.0,
        "fat_g": 7.0,
        "prep_min": 5,
        "ingredients": [
            {"item": "乳清蛋白粉", "amount": "25g"},
            {"item": "低脂牛奶", "amount": "250ml"},
            {"item": "香蕉", "amount": "40g"},
            {"item": "燕麦片", "amount": "10g"},
            {"item": "无糖花生酱", "amount": "5g"},
            {"item": "冰块", "amount": "3 块"},
            {"item": "肉桂粉", "amount": "少许"},
        ],
        "steps": [
            "燕麦片 10g 用 50ml 温水泡 3 分钟。",
            "香蕉 40g 掰段，与蛋白粉 25g、低脂牛奶 250ml 一起放入搅拌机。",
            "加入泡软的燕麦、无糖花生酱 5g 和冰块 3 块。",
            "高速搅打 40 秒至顺滑，倒入杯中，撒少许肉桂粉即可。",
        ],
        "timing_tip": "适合训练后 30 分钟内饮用，快速补充蛋白质和碳水。",
    },
]


def _summary(recipe: dict) -> dict:
    """构造不含 ingredients/steps 的食谱摘要（深拷贝）。"""
    return {key: copy.deepcopy(recipe[key]) for key in _SUMMARY_KEYS}


def _matches_query(recipe: dict, needle: str) -> bool:
    haystack = recipe["name"].lower() + "\n" + "\n".join(
        item["item"] for item in recipe["ingredients"]
    ).lower()
    return needle in haystack


def list_recipes(
    goal: str | None = None,
    slot: str | None = None,
    q: str | None = None,
) -> list[dict]:
    """按目标/餐段/关键词筛选食谱，返回摘要列表（不含做法与食材明细）。

    goal 与 slot 按标签包含过滤；q 对菜名和食材名做不区分大小写的包含匹配。
    """
    needle = q.lower() if q else None
    results: list[dict] = []
    for recipe in RECIPES:
        if goal is not None and goal not in recipe["goal_tags"]:
            continue
        if slot is not None and slot not in recipe["meal_slots"]:
            continue
        if needle is not None and not _matches_query(recipe, needle):
            continue
        results.append(_summary(recipe))
    return results


def get_recipe(recipe_id: str) -> dict | None:
    """按 id 返回完整食谱（含 ingredients/steps）的深拷贝；未找到返回 None。"""
    for recipe in RECIPES:
        if recipe["id"] == recipe_id:
            return copy.deepcopy(recipe)
    return None


def recommend(
    goal: str | None = None,
    slot: str | None = None,
    q: str | None = None,
    limit: int = 20,
) -> list[dict]:
    """按匹配度排序返回食谱摘要推荐。

    排序规则：goal 命中（goal_tags 含目标）排在"仅 maintain 兼容"
    （未命中但含 maintain）之前，同档内按 prep_min 升序，id 作为稳定 tiebreaker。
    """
    if goal is not None and goal not in _GOALS:
        return []
    if slot is not None and slot not in _SLOTS:
        return []
    if limit <= 0:
        return []

    needle = q.lower() if q else None
    ranked: list[tuple[int, int, str, dict]] = []
    for recipe in RECIPES:
        if slot is not None and slot not in recipe["meal_slots"]:
            continue
        if needle is not None and not _matches_query(recipe, needle):
            continue
        if goal is None:
            rank = 0
        elif goal in recipe["goal_tags"]:
            rank = 0
        elif "maintain" in recipe["goal_tags"]:
            rank = 1
        else:
            continue
        ranked.append((rank, recipe["prep_min"], recipe["id"], recipe))

    ranked.sort(key=lambda item: (item[0], item[1], item[2]))
    return [_summary(item[3]) for item in ranked[:limit]]
