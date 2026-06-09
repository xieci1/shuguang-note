"""
将旧版 history JSON 文件迁移到 SQLite 数据库。

可重复运行：已存在的 record_id 会跳过创建，图片会按 task_id + page_index 补齐。
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from backend.db import get_session, init_db  # noqa: E402
from backend.models import Creation, ImageTask, OutlinePage  # noqa: E402
from backend.services.history import get_history_service  # noqa: E402


HISTORY_DIR = ROOT_DIR / "history"


def load_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"跳过无法读取的文件: {path.name}, {exc}")
        return None


def migrate_record(record: dict) -> bool:
    service = get_history_service()
    record_id = record.get("id")
    if not record_id:
        return False

    with get_session() as session:
        exists = session.get(Creation, record_id) is not None

    if not exists:
        outline = record.get("outline") or {"raw": "", "pages": []}
        task_id = (record.get("images") or {}).get("task_id")
        with get_session() as session:
            creation = Creation(
                id=record_id,
                title=record.get("title") or "未命名创作",
                status=record.get("status") or "draft",
                thumbnail=record.get("thumbnail"),
                task_id=task_id,
                outline_raw=outline.get("raw", ""),
            )
            creation.created_at = _parse_dt(record.get("created_at"), creation.created_at)
            creation.updated_at = _parse_dt(record.get("updated_at"), creation.updated_at)
            session.add(creation)
            for position, page in enumerate(outline.get("pages", [])):
                session.add(
                    OutlinePage(
                        creation_id=record_id,
                        page_index=page.get("index", position),
                        type=page.get("type", "content"),
                        content=page.get("content", ""),
                    )
                )
            if task_id:
                task = session.get(ImageTask, task_id)
                if not task:
                    task = ImageTask(task_id=task_id)
                task.creation_id = task.creation_id or record_id
                task.status = record.get("status") or task.status or "draft"
                task.total = max(task.total or 0, len(outline.get("pages", [])))
                session.add(task)

    service.update_record(
        record_id,
        images=record.get("images"),
        status=record.get("status"),
        thumbnail=record.get("thumbnail"),
        content=record.get("content"),
    )
    task_id = (record.get("images") or {}).get("task_id")
    if task_id:
        service.scan_and_sync_task_images(task_id)
    return True


def _parse_dt(value, fallback):
    if not value:
        return fallback
    from datetime import datetime

    try:
        return datetime.fromisoformat(value)
    except Exception:
        return fallback


def main() -> int:
    init_db()
    if not HISTORY_DIR.exists():
        print("history 目录不存在，无需迁移")
        return 0

    migrated = 0
    for path in HISTORY_DIR.glob("*.json"):
        if path.name == "index.json":
            continue
        record = load_json(path)
        if record and migrate_record(record):
            migrated += 1

    service = get_history_service()
    scan_result = service.scan_all_tasks()
    print(f"迁移完成：记录 {migrated} 条，扫描任务 {scan_result.get('total_tasks', 0)} 个")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
