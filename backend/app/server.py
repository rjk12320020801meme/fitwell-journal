"""FastAPI 服务层：记录 API、周报、食谱、静态前端。

运行：
    cd fitwell-journal
    python -m uvicorn backend.app.server:app --host 127.0.0.1 --port 8000

核心逻辑不依赖 FastAPI；本文件是唯一的 web 层。
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .models import RECORD_TYPES, ValidationError
from .recipes import get_recipe, list_recipes
from .rhythm import rhythm_status, validate_settings
from .storage import JournalStore
from .trends import weekly_report

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"

app = FastAPI(
    title="FitWell Journal API",
    version="0.1.0",
    description="健身健康日志——趋势洞察，不构成医疗诊断。",
)

store = JournalStore()


# ---------- 健康检查 ----------
@app.get("/api/health")
def health():
    return {"status": "ok", "version": "0.1.0"}


# ---------- 记录 ----------
@app.post("/api/records/{record_type}", status_code=201)
def create_record(record_type: str, payload: dict):
    if record_type not in RECORD_TYPES:
        raise HTTPException(404, f"未知记录类型: {record_type}")
    try:
        return store.append(record_type, payload)
    except ValidationError as e:
        raise HTTPException(422, str(e))


@app.get("/api/records")
def list_records(
    date_from: str | None = Query(None, alias="from"),
    date_to: str | None = Query(None, alias="to"),
):
    return store.query(date_from, date_to)


@app.delete("/api/records/{record_type}/{record_id}", status_code=204)
def delete_record(record_type: str, record_id: str):
    if record_type not in RECORD_TYPES:
        raise HTTPException(404, f"未知记录类型: {record_type}")
    if not store.delete(record_type, record_id):
        raise HTTPException(404, "记录不存在")


# ---------- 周报 ----------
@app.get("/api/report/weekly")
def report_weekly(end_date: str | None = Query(None)):
    if end_date:
        try:
            from datetime import date as _date
            _date.fromisoformat(end_date)
        except ValueError:
            raise HTTPException(422, "end_date 需为 YYYY-MM-DD")
    return weekly_report(store.all_records(), end_date)


# ---------- 节奏（小闹钟） ----------
@app.get("/api/settings")
def get_settings():
    return store.load_settings()


@app.put("/api/settings")
def put_settings(payload: dict):
    try:
        settings = validate_settings(payload)
    except ValueError as e:
        raise HTTPException(422, str(e))
    return store.save_settings(settings)


@app.get("/api/rhythm/today")
def rhythm_today(now: str | None = Query(None, description="HH:MM，测试用")):
    if now:
        try:
            from .rhythm import _parse_hhmm
            _parse_hhmm(now)
        except ValueError:
            raise HTTPException(422, "now 需为 HH:MM")
    return rhythm_status(store.load_settings(), now)


# ---------- 食谱 ----------
@app.get("/api/recipes")
def recipes(
    goal: str | None = Query(None),
    slot: str | None = Query(None),
    q: str | None = Query(None),
):
    return list_recipes(goal=goal, slot=slot, q=q)


@app.get("/api/recipes/{recipe_id}")
def recipe_detail(recipe_id: str):
    r = get_recipe(recipe_id)
    if r is None:
        raise HTTPException(404, "食谱不存在")
    return r


# ---------- 静态前端（最后挂载，兜底到 index.html） ----------
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
