"""数据模型与校验（纯标准库）。

实体定义见 docs/data-model.md。所有模型均可 to_dict/from_dict 往返，
校验失败抛 ValidationError。
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field, fields, asdict
from datetime import datetime

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TIME_RE = re.compile(r"^\d{2}:\d{2}$")

MEAL_TYPES = {"breakfast", "lunch", "dinner", "snack"}
# v0.1.1：主观打分项（心情/压力/精力/饥饿/渴望）全部移除——只记录客观事实。
RECORD_TYPES = ("meal", "sleep", "body", "training", "lab")


class ValidationError(ValueError):
    """记录字段不合法。"""


def _check_date(v: str) -> str:
    if not isinstance(v, str) or not DATE_RE.match(v):
        raise ValidationError(f"date 需为 YYYY-MM-DD，收到: {v!r}")
    try:
        datetime.strptime(v, "%Y-%m-%d")
    except ValueError:
        raise ValidationError(f"date 不是有效日期: {v!r}")
    return v


def _check_time(v: str) -> str:
    if not isinstance(v, str) or not TIME_RE.match(v):
        raise ValidationError(f"time 需为 HH:MM，收到: {v!r}")
    hh, mm = int(v[:2]), int(v[3:])
    if hh > 23 or mm > 59:
        raise ValidationError(f"time 超出范围: {v!r}")
    return v


def _check_str(v, name: str, required: bool = False) -> str:
    if v is None or v == "":
        if required:
            raise ValidationError(f"{name} 必填")
        return ""
    if not isinstance(v, str):
        raise ValidationError(f"{name} 需为字符串")
    return v


def _check_int(v, name: str, lo=None, hi=None, required: bool = False):
    if v is None:
        if required:
            raise ValidationError(f"{name} 必填")
        return None
    if isinstance(v, bool) or not isinstance(v, int):
        raise ValidationError(f"{name} 需为整数，收到: {v!r}")
    if (lo is not None and v < lo) or (hi is not None and v > hi):
        raise ValidationError(f"{name} 超出范围 [{lo}, {hi}]: {v}")
    return v


def _check_num(v, name: str, lo=None, hi=None):
    if v is None:
        return None
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise ValidationError(f"{name} 需为数字，收到: {v!r}")
    v = float(v)
    if (lo is not None and v < lo) or (hi is not None and v > hi):
        raise ValidationError(f"{name} 超出范围 [{lo}, {hi}]: {v}")
    return v


def _new_id() -> str:
    return str(uuid.uuid4())


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


@dataclass
class MealEntry:
    date: str
    time: str
    meal_type: str
    description: str = ""
    portion: str = ""
    notes: str = ""
    id: str = field(default_factory=_new_id)
    created_at: str = field(default_factory=_now_iso)

    def validate(self) -> "MealEntry":
        _check_date(self.date)
        _check_time(self.time)
        if self.meal_type not in MEAL_TYPES:
            raise ValidationError(f"meal_type 需为 {sorted(MEAL_TYPES)} 之一: {self.meal_type!r}")
        _check_str(self.description, "description")
        _check_str(self.portion, "portion")
        _check_str(self.notes, "notes")
        return self


@dataclass
class SleepEntry:
    date: str
    bed_time: str
    wake_time: str
    quality: int = None
    awakenings: int = None
    nap_min: int = None
    id: str = field(default_factory=_new_id)
    created_at: str = field(default_factory=_now_iso)

    def validate(self) -> "SleepEntry":
        _check_date(self.date)
        _check_time(self.bed_time)
        _check_time(self.wake_time)
        _check_int(self.quality, "quality", 1, 5)
        _check_int(self.awakenings, "awakenings", 0, 50)
        _check_int(self.nap_min, "nap_min", 0, 600)
        return self


@dataclass
class BodyEntry:
    date: str
    weight_kg: float = None
    waist_cm: float = None
    body_fat_pct: float = None
    resting_hr: float = None
    hrv_ms: float = None
    id: str = field(default_factory=_new_id)
    created_at: str = field(default_factory=_now_iso)

    def validate(self) -> "BodyEntry":
        _check_date(self.date)
        _check_num(self.weight_kg, "weight_kg", 20, 400)
        _check_num(self.waist_cm, "waist_cm", 30, 250)
        _check_num(self.body_fat_pct, "body_fat_pct", 0, 70)
        _check_num(self.resting_hr, "resting_hr", 20, 200)
        _check_num(self.hrv_ms, "hrv_ms", 1, 500)
        return self


@dataclass
class TrainingEntry:
    date: str
    time: str
    type: str
    duration_min: int = None
    rpe: int = None
    id: str = field(default_factory=_new_id)
    created_at: str = field(default_factory=_now_iso)

    def validate(self) -> "TrainingEntry":
        _check_date(self.date)
        _check_time(self.time)
        _check_str(self.type, "type", required=True)
        _check_int(self.duration_min, "duration_min", 1, 1440, required=True)
        _check_int(self.rpe, "rpe", 1, 10)
        return self


@dataclass
class LabEntry:
    date: str
    fasting_glucose: float = None
    fasting_insulin: float = None
    hba1c: float = None
    total_chol: float = None
    ldl: float = None
    hdl: float = None
    triglycerides: float = None
    id: str = field(default_factory=_new_id)
    created_at: str = field(default_factory=_now_iso)

    def validate(self) -> "LabEntry":
        _check_date(self.date)
        _check_num(self.fasting_glucose, "fasting_glucose", 1, 50)
        _check_num(self.fasting_insulin, "fasting_insulin", 0, 500)
        _check_num(self.hba1c, "hba1c", 2, 25)
        _check_num(self.total_chol, "total_chol", 0.5, 50)
        _check_num(self.ldl, "ldl", 0.1, 50)
        _check_num(self.hdl, "hdl", 0.1, 20)
        _check_num(self.triglycerides, "triglycerides", 0.1, 50)
        return self


MODEL_BY_TYPE = {
    "meal": MealEntry,
    "sleep": SleepEntry,
    "body": BodyEntry,
    "training": TrainingEntry,
    "lab": LabEntry,
}


def to_dict(entry) -> dict:
    return asdict(entry)


def from_dict(record_type: str, data: dict):
    """从 dict 构造并校验记录；忽略未知字段，保留 id/created_at（若提供）。"""
    model = MODEL_BY_TYPE.get(record_type)
    if model is None:
        raise ValidationError(f"未知记录类型: {record_type!r}")
    if not isinstance(data, dict):
        raise ValidationError("记录需为对象")
    names = {f.name for f in fields(model)}
    kwargs = {k: v for k, v in data.items() if k in names}
    try:
        entry = model(**kwargs)
    except TypeError as e:
        raise ValidationError(f"字段缺失或多余: {e}")
    return entry.validate()


def validate_record(record_type: str, data: dict):
    """校验并返回规范化 dict（含 id/created_at）。"""
    return to_dict(from_dict(record_type, data))
