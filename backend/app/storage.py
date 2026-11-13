"""JSON 文件存储（纯标准库）。

单文件、按类型分组；读写带基本线程锁。存储格式见 docs/data-model.md §2。
"""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path

from .models import RECORD_TYPES, ValidationError, validate_record

DEFAULT_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "journal.json"


class JournalStore:
    def __init__(self, path: str | os.PathLike | None = None):
        self.path = Path(path or os.environ.get("FITWELL_DATA") or DEFAULT_DATA_PATH)
        self._lock = threading.Lock()

    # ---------- 基础读写 ----------
    def _empty(self) -> dict:
        data = {"version": 1}
        for t in RECORD_TYPES:
            data[t] = []
        return data

    def load(self) -> dict:
        if not self.path.exists():
            return self._empty()
        with open(self.path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for t in RECORD_TYPES:
            data.setdefault(t, [])
        return data

    def save(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)

    # ---------- 业务操作 ----------
    def append(self, record_type: str, payload: dict) -> dict:
        """校验并追加一条记录，返回含 id 的记录 dict。"""
        record = validate_record(record_type, payload)  # 校验失败抛 ValidationError
        with self._lock:
            data = self.load()
            data[record_type].append(record)
            self.save(data)
        return record

    def delete(self, record_type: str, record_id: str) -> bool:
        if record_type not in RECORD_TYPES:
            raise ValidationError(f"未知记录类型: {record_type!r}")
        with self._lock:
            data = self.load()
            before = len(data[record_type])
            data[record_type] = [r for r in data[record_type] if r.get("id") != record_id]
            if len(data[record_type]) == before:
                return False
            self.save(data)
        return True

    def query(self, date_from: str | None = None, date_to: str | None = None) -> dict:
        """按日期区间过滤（含端点），返回按类型分组的记录。"""
        with self._lock:
            data = self.load()
        out = {}
        for t in RECORD_TYPES:
            rows = data[t]
            if date_from:
                rows = [r for r in rows if r.get("date", "") >= date_from]
            if date_to:
                rows = [r for r in rows if r.get("date", "") <= date_to]
            out[t] = sorted(rows, key=lambda r: (r.get("date", ""), r.get("time", ""), r.get("created_at", "")))
        return out

    def all_records(self) -> dict:
        return self.query()
