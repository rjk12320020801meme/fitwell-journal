"""日聚合、周报 series 与趋势卡片（纯标准库）。

build_days() 把原始记录聚合成规则引擎需要的 day dict；
weekly_report() 组装 docs/insights-rules.md §5 的周报结构。
"""
from __future__ import annotations

import statistics
from datetime import date, timedelta

from .rules import correlation_cards, score_metabolic, score_sleep

CORRELATION_LOOKBACK_DAYS = 28  # 关联卡片用近 28 天样本（证据比 7 天可靠）


# ---------- 时点工具 ----------

def parse_hhmm(s: str) -> int:
    """HH:MM -> 当日分钟数。"""
    hh, mm = s.split(":")
    return int(hh) * 60 + int(mm)


def bed_offset(bed_min: int) -> int:
    """就寝时刻相对 20:00 的分钟偏移（0–1439），用于波动统计与作图。"""
    return (bed_min - 20 * 60) % 1440


def sleep_duration(bed_min: int, wake_min: int) -> float:
    """睡眠小时数；起床早于上床视为跨午夜。"""
    return ((wake_min - bed_min) % 1440) / 60.0


def last_meal_to_bed(bed_min: int, last_meal_min: int) -> float:
    """末餐→上床的分钟数；负值表示餐在上床之后（夜宵）。"""
    delta = bed_min - last_meal_min
    if delta < -720:  # 上床在午夜后、末餐在前一晚
        delta += 1440
    return delta


# ---------- 日聚合 ----------

def build_days(records: dict) -> list[dict]:
    """records 为 storage.query() 形状（按类型分组的记录列表）→ day dict 列表（按日期升序）。

    同日多条同类记录取最后一条（created_at 最新）；training 只看有无。
    """
    dates: set[str] = set()
    for rows in records.values():
        for r in rows:
            if r.get("date"):
                dates.add(r["date"])

    by_date: dict[str, dict] = {}
    for d_str in sorted(dates):
        meals = [r for r in records.get("meal", []) if r["date"] == d_str]
        sleeps = [r for r in records.get("sleep", []) if r["date"] == d_str]
        trains = [r for r in records.get("training", []) if r["date"] == d_str]
        bodies = [r for r in records.get("body", []) if r["date"] == d_str]

        meal_times = sorted(parse_hhmm(m["time"]) for m in meals)
        snack_count = sum(1 for m in meals if m.get("meal_type") == "snack")

        day = {
            "date": d_str,
            "meal_times": meal_times,
            "meal_count": len(meals),
            "snack_count": snack_count,
            "window_h": None,
            "last_meal_to_bed_min": None,
            "eat_within_2h_before_bed": False,
            "bed_min": None,
            "wake_min": None,
            "bed_offset_min": None,
            "sleep_h": None,
            "trained": bool(trains),
            "weight_kg": None,
        }

        if len(meal_times) >= 1:
            day["window_h"] = (meal_times[-1] - meal_times[0]) / 60.0

        if sleeps:
            s = sleeps[-1]
            day["bed_min"] = parse_hhmm(s["bed_time"])
            day["wake_min"] = parse_hhmm(s["wake_time"])
            day["bed_offset_min"] = bed_offset(day["bed_min"])
            day["sleep_h"] = sleep_duration(day["bed_min"], day["wake_min"])

        if meal_times and day["bed_min"] is not None:
            gap = last_meal_to_bed(day["bed_min"], meal_times[-1])
            day["last_meal_to_bed_min"] = gap
            day["eat_within_2h_before_bed"] = -120 <= gap <= 120

        if bodies:
            w = [b.get("weight_kg") for b in bodies if b.get("weight_kg") is not None]
            if w:
                day["weight_kg"] = w[-1]

        by_date[d_str] = day

    return [by_date[d] for d in sorted(by_date)]


# ---------- 周报 series ----------

def _daterange(start: str, end: str) -> list[str]:
    s, e = date.fromisoformat(start), date.fromisoformat(end)
    return [(s + timedelta(days=i)).isoformat() for i in range((e - s).days + 1)]


def build_series(days: list[dict], start: str, end: str) -> dict:
    by_date = {d["date"]: d for d in days}
    dates = _daterange(start, end)
    out = {
        "dates": dates,
        "eating_window_h": [],
        "sleep_duration_h": [],
        "bed_offset_min": [],
        "weight_kg": [],
    }
    for d_str in dates:
        d = by_date.get(d_str)
        if d is None:
            for key in out:
                if key != "dates":
                    out[key].append(None)
            continue
        # 单餐日没有"进食窗口"可言，作图跳过
        out["eating_window_h"].append(d["window_h"] if d["meal_count"] >= 2 else None)
        out["sleep_duration_h"].append(d["sleep_h"])
        out["bed_offset_min"].append(d["bed_offset_min"])
        out["weight_kg"].append(d["weight_kg"])
    return out


# ---------- 趋势卡片 ----------

def _mean(xs: list[float]) -> float | None:
    return statistics.fmean(xs) if xs else None


def trend_cards(days: list[dict], start: str, end: str) -> list[dict]:
    """周环比趋势卡片：近 7 天 vs 前 7 天。"""
    cur_start = (date.fromisoformat(end) - timedelta(days=6)).isoformat()
    prev_start = (date.fromisoformat(cur_start) - timedelta(days=7)).isoformat()
    prev_end = (date.fromisoformat(cur_start) - timedelta(days=1)).isoformat()

    cur = [d for d in days if cur_start <= d["date"] <= end]
    prev = [d for d in days if prev_start <= d["date"] <= prev_end]
    cards: list[dict] = []

    def add(title: str, detail: str, direction: str, evidence: int):
        cards.append({"kind": "trend", "title": title, "detail": detail,
                      "evidence_days": evidence, "direction": direction})

    # 进食窗口（≥2 餐的天）
    cw = [d["window_h"] for d in cur if d["meal_count"] >= 2]
    pw = [d["window_h"] for d in prev if d["meal_count"] >= 2]
    if cw and pw and len(cw) >= 3 and len(pw) >= 3:
        delta = _mean(cw) - _mean(pw)
        if abs(delta) >= 0.5:
            word = "缩短" if delta < 0 else "延长"
            tail = "，方向良好" if delta < 0 else "，值得留意"
            add("进食窗口变化", f"近一周你的进食窗口平均{word}了 {abs(delta):.1f} 小时{tail}",
                "down" if delta < 0 else "up", len(cw) + len(pw))

    # 睡眠时长
    cs = [d["sleep_h"] for d in cur if d["sleep_h"] is not None]
    ps = [d["sleep_h"] for d in prev if d["sleep_h"] is not None]
    if cs and ps and len(cs) >= 3 and len(ps) >= 3:
        delta = _mean(cs) - _mean(ps)
        if abs(delta) >= 20 / 60:
            word = "延长" if delta > 0 else "缩短"
            tail = "，方向良好" if delta > 0 else "，多留意休息"
            add("睡眠时长变化", f"近一周你的平均睡眠{word}了 {abs(delta) * 60:.0f} 分钟{tail}",
                "up" if delta > 0 else "down", len(cs) + len(ps))

    # 体重（测量点 ≥3/周）
    cb = [d["weight_kg"] for d in cur if d["weight_kg"] is not None]
    pb = [d["weight_kg"] for d in prev if d["weight_kg"] is not None]
    if len(cb) >= 3 and len(pb) >= 3:
        delta = _mean(cb) - _mean(pb)
        if abs(delta) >= 0.5:
            word = "上升" if delta > 0 else "下降"
            add("体重变化", f"近一周体重均值{word}了 {abs(delta):.1f} 公斤（基于 {len(cb) + len(pb)} 次测量）",
                "up" if delta > 0 else "down", len(cb) + len(pb))

    return cards


# ---------- 周报组装 ----------

def _empty_score() -> dict:
    return {"score": None, "grade": None, "factors": []}


def weekly_report(records: dict, end_date: str | None = None) -> dict:
    """组装周报。records 为 storage.query() 全量形状。"""
    all_days = build_days(records)
    end = end_date or date.today().isoformat()
    start = (date.fromisoformat(end) - timedelta(days=6)).isoformat()
    period_days = [d for d in all_days if start <= d["date"] <= end]

    corr_start = (date.fromisoformat(end) - timedelta(days=CORRELATION_LOOKBACK_DAYS - 1)).isoformat()
    corr_days = [d for d in all_days if corr_start <= d["date"] <= end]

    metabolic = score_metabolic(period_days) or _empty_score()
    sleep = score_sleep(period_days) or _empty_score()
    cards = trend_cards(all_days, start, end) + correlation_cards(corr_days)

    return {
        "period": {"start": start, "end": end},
        "metabolic": metabolic,
        "sleep": sleep,
        "cards": cards,
        "series": build_series(all_days, start, end),
    }
