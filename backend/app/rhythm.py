"""今日节奏（小闹钟）：基于进食窗口与作息目标，给出温和的当下提示。

产品宗旨：健身人的小闹钟——只提示节奏，不评判、不制造焦虑。
输出为人话文案，前端直接展示。纯标准库。
"""
from __future__ import annotations

from datetime import datetime

SETTINGS_KEYS = ("window_start", "window_end", "bed_target", "wake_target")

DEFAULT_SETTINGS = {
    "window_start": "10:00",   # 进食窗口开启
    "window_end": "19:00",     # 进食窗口收尾
    "bed_target": "23:00",     # 目标就寝
    "wake_target": "07:00",    # 目标起床
}


def _parse_hhmm(s: str) -> int:
    hh, mm = s.split(":")
    h, m = int(hh), int(mm)
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise ValueError(f"时间超出范围: {s!r}")
    return h * 60 + m


def validate_settings(payload: dict) -> dict:
    """校验并规范化设置；缺失的键回落默认值。非法抛 ValueError。"""
    out = dict(DEFAULT_SETTINGS)
    for k in SETTINGS_KEYS:
        if k in payload and payload[k] is not None:
            v = payload[k]
            if not isinstance(v, str) or len(v) != 5 or v[2] != ":":
                raise ValueError(f"{k} 需为 HH:MM，收到: {v!r}")
            try:
                minute = _parse_hhmm(v)
            except ValueError:
                raise ValueError(f"{k} 需为 HH:MM，收到: {v!r}")
            if minute >= 1440:
                raise ValueError(f"{k} 超出一天范围: {v!r}")
            out[k] = v
    return out


def _fmt(minute: int) -> str:
    return f"{minute // 60 % 24:02d}:{minute % 60:02d}"


def _fmt_gap(minutes: int) -> str:
    """把分钟差写成'X 小时 Y 分钟'。"""
    h, m = divmod(max(0, minutes), 60)
    if h and m:
        return f"{h} 小时 {m} 分钟"
    if h:
        return f"{h} 小时"
    return f"{m} 分钟"


def rhythm_status(settings: dict | None = None, now: str | None = None) -> dict:
    """当前时刻的节奏提示。

    settings: validate_settings 的输出（或部分设置）；now: "HH:MM"（测试用，默认系统时间）。
    返回 {now, phase, title, message, next_time, next_label}。
    """
    s = validate_settings(settings or {})
    now_min = _parse_hhmm(now) if now else datetime.now().hour * 60 + datetime.now().minute

    wake = _parse_hhmm(s["wake_target"])
    bed = _parse_hhmm(s["bed_target"])
    w_start = _parse_hhmm(s["window_start"])
    w_end = _parse_hhmm(s["window_end"])
    pre_bed = (bed - 120) % 1440

    def rel(x: int) -> int:
        return (x - wake) % 1440

    # 睡眠时段：从就寝起、到目标起床止（支持跨午夜）
    awake_len = (bed - wake) % 1440 or 1440
    if rel(now_min) >= awake_len:
        return {
            "now": _fmt(now_min),
            "phase": "sleep",
            "title": "睡眠时段 😴",
            "message": "这是你的目标睡眠时段，睡个好觉比什么都重要。",
            "next_time": s["wake_target"],
            "next_label": "目标起床",
        }

    r_now = rel(now_min)
    seg = [
        (rel(w_start), "morning", "早安 ☀️",
         f"距离你的进食窗口开启还有 {{gap}}。起床后先喝杯水，不着急。",
         s["window_start"], "进食窗口开启"),
        (rel(w_end), "eating", "进食窗口进行中 🍽️",
         "现在是你补充营养的时间，记得吃够蛋白质和水分。",
         s["window_end"], "进食窗口收尾"),
        (rel(pre_bed), "wind_down", "收尾过渡 🌿",
         "今天的进食窗口已收尾，距离目标就寝还有 {gap}。可以安排点轻松的事。",
         _fmt(pre_bed), "睡前收尾开始"),
        (rel(bed), "pre_bed", "睡前收尾 🌙",
         "进入睡前 2 小时啦，今天可以收尾了。早点休息，明天继续。",
         s["bed_target"], "目标就寝"),
    ]

    # 找到当前所处阶段（按 rel 边界单调扫描；异常配置兜底到最后一个阶段）
    phase = seg[-1]
    for item in seg:
        if r_now < item[0]:
            phase = item
            break
    # 边界之前的阶段（r_now 小于第一个边界 → 晨间）
    if r_now < seg[0][0]:
        phase = seg[0]

    _, key, title, msg_tpl, next_time, next_label = phase
    gap_to_next = (rel(_parse_hhmm(next_time)) - r_now) % 1440
    message = msg_tpl.replace("{gap}", _fmt_gap(gap_to_next))

    return {
        "now": _fmt(now_min),
        "phase": key,
        "title": title,
        "message": message,
        "next_time": next_time,
        "next_label": next_label,
    }
