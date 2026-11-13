"""规则引擎：代谢规律分、睡眠规律分、关联卡片（纯标准库）。

规格见 docs/insights-rules.md。所有输出为启发式趋势洞察，措辞遵守红线：
只说"数据显示…趋势/建议关注"，禁止诊断性语言（BANNED_WORDS）。
输入统一为 trends.build_days() 产出的"日聚合 dict"（day dict）：
  date, meal_times[min], meal_count, snack_count, window_h,
  last_meal_to_bed_min, eat_within_2h_before_bed,
  bed_min, wake_min, bed_offset_min(20:00锚点), sleep_h,
  stress, energy, trained
"""
from __future__ import annotations

import statistics
from datetime import date, timedelta

# ---------- 措辞红线 ----------
BANNED_WORDS = ("抵抗", "诊断", "患病", "风险人群", "糖尿病前期", "确诊", "病症")

MIN_METABOLIC_DAYS = 2
MIN_SLEEP_DAYS = 3
MIN_GROUP = 3  # 关联卡片组内最小样本天数


def check_wording(text: str) -> bool:
    """返回 True 表示文案通过红线检查。"""
    return not any(w in text for w in BANNED_WORDS)


def grade_of(score: float | None) -> str | None:
    if score is None:
        return None
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    if score >= 55:
        return "C"
    return "D"


# ---------- 代谢规律分 ----------

def _window_score(hours: float) -> int:
    if 8 <= hours <= 10:
        return 100
    if 7 <= hours < 8 or 10 < hours <= 11:
        return 75
    if 6 <= hours < 7 or 11 < hours <= 12:
        return 55
    return 35


def _gap_score(minutes: float) -> int:
    """末餐-入睡间隔（分钟）。负值（夜宵/饭后即睡）给最低分。"""
    if minutes >= 120:
        return 100
    if minutes >= 60:
        return 70
    if minutes >= 30:
        return 45
    return 25


def _rhythm_score(count: int) -> int:
    if 3 <= count <= 5:
        return 100
    if count in (2, 6):
        return 70
    return 45


def _late_eating_score(eat_within_2h: bool) -> int:
    return 30 if eat_within_2h else 100


METABOLIC_FACTORS = (
    ("进食窗口时长", 0.35),
    ("末餐-入睡间隔", 0.30),
    ("进食节奏", 0.20),
    ("睡前2h进食", 0.15),
)


def score_metabolic(days: list[dict]) -> dict | None:
    """代谢规律分。有效日 = 有进食且有睡眠记录；不足 MIN_METABOLIC_DAYS 返回 None。"""
    valid = [d for d in days if d.get("meal_count", 0) >= 1 and d.get("bed_min") is not None]
    if len(valid) < MIN_METABOLIC_DAYS:
        return None

    windows = [d["window_h"] for d in valid]
    gaps = [d["last_meal_to_bed_min"] for d in valid]
    counts = [d["meal_count"] for d in valid]
    late_days = sum(1 for d in valid if d["eat_within_2h_before_bed"])

    f_window = statistics.fmean(_window_score(w) for w in windows)
    f_gap = statistics.fmean(_gap_score(g) for g in gaps)
    f_rhythm = statistics.fmean(_rhythm_score(c) for c in counts)
    f_late = statistics.fmean(_late_eating_score(d["eat_within_2h_before_bed"]) for d in valid)

    scores = [f_window, f_gap, f_rhythm, f_late]
    total = sum(s * w for s, (_, w) in zip(scores, METABOLIC_FACTORS))

    details = [
        f"进食窗口平均 {statistics.fmean(windows):.1f} 小时（参考 8–10 小时）",
        f"最后一餐到上床平均间隔 {statistics.fmean(gaps):.0f} 分钟（参考 ≥120 分钟）",
        f"每日进食 {statistics.fmean(counts):.1f} 次（参考 3–5 次）",
        f"近 {len(valid)} 天中有 {late_days} 天在睡前 2 小时内进食",
    ]
    factors = [
        {"name": name, "score": round(s, 1), "weight": w, "detail": detail}
        for (name, w), s, detail in zip(METABOLIC_FACTORS, scores, details)
    ]
    return {"score": round(total), "grade": grade_of(total), "factors": factors, "days_used": len(valid)}


# ---------- 睡眠规律分 ----------

def _duration_score(hours: float) -> int:
    if 7 <= hours <= 9:
        return 100
    if 6 <= hours < 7 or 9 < hours <= 9.5:
        return 75
    if 5 <= hours < 6 or 9.5 < hours <= 10:
        return 50
    return 30


def _spread_score(stdev_min: float) -> int:
    if stdev_min <= 30:
        return 100
    if stdev_min <= 60:
        return 75
    if stdev_min <= 90:
        return 50
    return 30


def _jetlag_score(diff_min: float) -> int:
    if diff_min <= 60:
        return 100
    if diff_min <= 120:
        return 70
    return 40


SLEEP_FACTORS = (
    ("睡眠时长", 0.35),
    ("就寝时刻波动", 0.25),
    ("起床时刻波动", 0.25),
    ("社交时差", 0.15),
)


def score_sleep(days: list[dict]) -> dict | None:
    """睡眠规律分。有效日 = 有睡眠记录；不足 MIN_SLEEP_DAYS 返回 None。"""
    valid = [d for d in days if d.get("sleep_h") is not None]
    if len(valid) < MIN_SLEEP_DAYS:
        return None

    durations = [d["sleep_h"] for d in valid]
    bed_offsets = [d["bed_offset_min"] for d in valid]
    wakes = [d["wake_min"] for d in valid]

    f_dur = statistics.fmean(_duration_score(h) for h in durations)
    bed_std = statistics.pstdev(bed_offsets) if len(bed_offsets) > 1 else 0.0
    wake_std = statistics.pstdev(wakes) if len(wakes) > 1 else 0.0
    f_bed = _spread_score(bed_std)
    f_wake = _spread_score(wake_std)

    # 社交时差：工作日 vs 周末就寝偏移均值差（样本不足给中性 70）
    weekday_beds, weekend_beds = [], []
    for d in valid:
        try:
            wd = date.fromisoformat(d["date"]).weekday()
        except ValueError:
            continue
        (weekend_beds if wd >= 5 else weekday_beds).append(d["bed_offset_min"])
    if len(weekday_beds) >= 3 and len(weekend_beds) >= 2:
        jetlag_min = abs(statistics.fmean(weekend_beds) - statistics.fmean(weekday_beds))
        f_jl = _jetlag_score(jetlag_min)
        jl_detail = f"工作日与周末就寝均值相差 {jetlag_min:.0f} 分钟（参考 ≤60 分钟）"
    else:
        f_jl, jl_detail = 70, "社交时差需要更多工作日/周末样本，暂给中性分"

    scores = [f_dur, f_bed, f_wake, f_jl]
    total = sum(s * w for s, (_, w) in zip(scores, SLEEP_FACTORS))

    details = [
        f"平均睡眠 {statistics.fmean(durations):.1f} 小时（参考 7–9 小时）",
        f"就寝时刻波动 ±{bed_std:.0f} 分钟（参考 ≤30 分钟）",
        f"起床时刻波动 ±{wake_std:.0f} 分钟（参考 ≤30 分钟）",
        jl_detail,
    ]
    factors = [
        {"name": name, "score": round(s, 1), "weight": w, "detail": detail}
        for (name, w), s, detail in zip(SLEEP_FACTORS, scores, details)
    ]
    return {"score": round(total), "grade": grade_of(total), "factors": factors, "days_used": len(valid)}


# ---------- 关联卡片 ----------

def _mean(xs: list[float]) -> float:
    return statistics.fmean(xs) if xs else 0.0


def correlation_cards(days: list[dict]) -> list[dict]:
    """组间对比的关联卡片。任一组样本 < MIN_GROUP 天不生成；差异过小不生成。"""
    cards: list[dict] = []
    by_date = {d["date"]: d for d in days}

    def next_day(d: dict) -> dict | None:
        try:
            nxt = date.fromisoformat(d["date"]) + timedelta(days=1)
        except ValueError:
            return None
        return by_date.get(nxt.isoformat())

    # 1) 睡眠不足 6h 与次日加餐
    short, base = [], []
    for d in days:
        if d.get("sleep_h") is None:
            continue
        nxt = next_day(d)
        if nxt is None:
            continue
        (short if d["sleep_h"] < 6 else base).append(nxt["snack_count"])
    if len(short) >= MIN_GROUP and len(base) >= MIN_GROUP:
        delta = _mean(short) - _mean(base)
        if abs(delta) >= 0.2:
            cards.append({
                "kind": "correlation",
                "title": "睡眠不足与加餐",
                "detail": f"睡眠不足 6 小时的日子，次日加餐次数平均多 {delta:.1f} 次（基于 {len(short) + len(base)} 天数据）",
                "evidence_days": len(short) + len(base),
                "direction": "up" if delta > 0 else "down",
            })

    # 2) 压力与睡前 2h 进食
    high = [d for d in days if d.get("stress") is not None and d["stress"] >= 4]
    low = [d for d in days if d.get("stress") is not None and d["stress"] <= 2]
    if len(high) >= MIN_GROUP and len(low) >= MIN_GROUP:
        share_high = sum(1 for d in high if d["eat_within_2h_before_bed"]) / len(high)
        share_low = sum(1 for d in low if d["eat_within_2h_before_bed"]) / len(low)
        diff_pp = (share_high - share_low) * 100
        if abs(diff_pp) >= 10:
            cards.append({
                "kind": "correlation",
                "title": "压力与睡前进食",
                "detail": f"压力较高的日子，睡前两小时进食的概率高出 {abs(diff_pp):.0f}%（基于 {len(high) + len(low)} 天数据）",
                "evidence_days": len(high) + len(low),
                "direction": "up" if diff_pp > 0 else "down",
            })

    # 3) 长进食窗口与次日精力
    long_w, mid_w = [], []
    for d in days:
        if d.get("window_h") is None:
            continue
        nxt = next_day(d)
        if nxt is None or nxt.get("energy") is None:
            continue
        if d["window_h"] > 11:
            long_w.append(nxt["energy"])
        elif 8 <= d["window_h"] <= 10:
            mid_w.append(nxt["energy"])
    if len(long_w) >= MIN_GROUP and len(mid_w) >= MIN_GROUP:
        delta = _mean(long_w) - _mean(mid_w)
        if abs(delta) >= 0.3:
            cards.append({
                "kind": "correlation",
                "title": "长进食窗口与次日精力",
                "detail": f"进食窗口超过 11 小时后，次日精力评分平均低 {abs(delta):.1f} 分（基于 {len(long_w) + len(mid_w)} 天数据）",
                "evidence_days": len(long_w) + len(mid_w),
                "direction": "down" if delta < 0 else "up",
            })

    # 4) 训练与入睡时刻
    trained = [d for d in days if d.get("trained") and d.get("bed_offset_min") is not None]
    untrained = [d for d in days if not d.get("trained") and d.get("bed_offset_min") is not None]
    if len(trained) >= MIN_GROUP and len(untrained) >= MIN_GROUP:
        diff_min = _mean([d["bed_offset_min"] for d in trained]) - _mean([d["bed_offset_min"] for d in untrained])
        if abs(diff_min) >= 15:
            word = "提前" if diff_min < 0 else "推迟"
            cards.append({
                "kind": "correlation",
                "title": "训练与入睡时刻",
                "detail": f"训练日你的入睡时间平均{word} {abs(diff_min):.0f} 分钟（基于 {len(trained) + len(untrained)} 天数据）",
                "evidence_days": len(trained) + len(untrained),
                "direction": "down" if diff_min < 0 else "up",
            })

    return cards
