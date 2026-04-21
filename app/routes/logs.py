import os
import json
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session
from app.database import engine
from app.models.projects import Projects
from app.services.auth import get_current_user
from app.services.log_parser import (
    sync_project_logs,
    get_meta_path,
    load_meta,
)
from app.services.log_parser import sync_project_logs, load_meta, save_meta
from app.utils.file_helpers import get_jsonl_path

router = APIRouter()


def get_project_or_404(project_id: int) -> Projects:
    with Session(engine) as session:
        project = session.get(Projects, project_id)
        if not project or project.is_archived:
            raise HTTPException(status_code=404, detail="Project not found")
        return project


def read_jsonl(project_id: int) -> list[dict]:
    path = get_jsonl_path(project_id)
    if not os.path.exists(path):
        return []
    logs = []
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                entry["_line"] = i + 1
                logs.append(entry)
            except Exception:
                continue
    return logs


@router.post("/{project_id}/logs/sync")
def sync_logs(project_id: int, user=Depends(get_current_user)):
    project = get_project_or_404(project_id)
    try:
        result = sync_project_logs(project_id, project.location)
        return {"success": True, **result}
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {e}")


@router.get("/{project_id}/logs/meta")
def get_meta(project_id: int, user=Depends(get_current_user)):
    """Returns parse metadata — which files were parsed, when, how many lines."""
    get_project_or_404(project_id)
    return load_meta(project_id)


@router.get("/{project_id}/logs")
def get_logs(
    project_id: int,
    date_range: Optional[str] = Query(None),
    date_from:  Optional[str] = Query(None),
    date_to:    Optional[str] = Query(None),
    level:      Optional[str] = Query(None),
    keyword:    Optional[str] = Query(None),
    page:       int           = Query(1,   ge=1),
    page_size:  int           = Query(100, ge=1, le=1000),
    user=Depends(get_current_user)
):
    get_project_or_404(project_id)
    logs = read_jsonl(project_id)

    if not logs:
        return {"total": 0, "page": 1, "pages": 0, "logs": [], "synced": False}

    # ── Date filter ───────────────────────────────────────────────────────────
    now = datetime.utcnow()
    if date_range == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now
    elif date_range == "7d":
        start = now - timedelta(days=7)
        end = now
    elif date_range == "30d":
        start = now - timedelta(days=30)
        end = now
    elif date_range == "custom" and date_from and date_to:
        start = datetime.strptime(date_from, "%Y-%m-%d")
        end   = datetime.strptime(date_to,   "%Y-%m-%d").replace(hour=23, minute=59, second=59)
    else:
        start = end = None

    if start and end:
        filtered = []
        for log in logs:
            ts = log.get("timestamp")
            if not ts:
                continue
            try:
                if start <= datetime.fromisoformat(str(ts)) <= end:
                    filtered.append(log)
            except Exception:
                continue
        logs = filtered

    # ── Level filter ──────────────────────────────────────────────────────────
    if level:
        logs = [l for l in logs if str(l.get("level", "")).upper() == level.upper()]

    # ── Keyword filter ────────────────────────────────────────────────────────
    if keyword:
        kw = keyword.lower()
        logs = [l for l in logs if kw in json.dumps(l).lower()]

    # ── Pagination ────────────────────────────────────────────────────────────
    total     = len(logs)
    start_idx = (page - 1) * page_size
    paginated = logs[start_idx: start_idx + page_size]

    return {
        "total":  total,
        "page":   page,
        "pages":  -(-total // page_size),
        "logs":   paginated,
        "synced": True,
    }

@router.get("/{project_id}/logs/columns")
def get_columns(project_id: int, user=Depends(get_current_user)):
    get_project_or_404(project_id)
    meta = load_meta(project_id)
    return {
        "column_map":       meta.get("column_map", {}),
        "detected_columns": meta.get("detected_columns", []),
        "format_changed":   meta.get("format_changed", False),
        "prev_columns":     meta.get("prev_columns", []),
    }

@router.post("/{project_id}/logs/columns")
def save_columns(
    project_id: int,
    payload: dict,
    user=Depends(get_current_user)
):
    get_project_or_404(project_id)
    meta = load_meta(project_id)
    meta["column_map"]     = payload.get("column_map", {})
    meta["format_changed"] = False   # clear the flag once user has acknowledged
    save_meta(project_id, meta)
    return {"success": True}