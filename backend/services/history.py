"""
数据库版历史记录服务。

对外保持原 HistoryService 方法和返回结构，内部使用 SQLite/SQLAlchemy 管理创作、大纲页、图片和内容。
"""

import json
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, func, select

from backend.db import get_session, init_db
from backend.models import Creation, GeneratedContent, GeneratedImage, ImageTask, OutlinePage, PublishDraft, PublishJob


class RecordStatus:
    DRAFT = "draft"
    GENERATING = "generating"
    PARTIAL = "partial"
    COMPLETED = "completed"
    ERROR = "error"


PUBLISHED_FILTER = "published"
PUBLISHED_JOB_STATUSES = {"ready_for_review", "published"}


class HistoryService:
    def __init__(self):
        self.root_dir = Path(__file__).resolve().parent.parent.parent
        self.history_dir = str(self.root_dir / "history")
        os.makedirs(self.history_dir, exist_ok=True)
        init_db()

    def create_record(self, topic: str, outline: Dict, task_id: Optional[str] = None, user_id: Optional[str] = None) -> str:
        record_id = str(uuid.uuid4())
        now = datetime.now()
        pages = outline.get("pages", [])

        with get_session() as session:
            creation = Creation(
                id=record_id,
                title=topic,
                status=RecordStatus.DRAFT,
                task_id=task_id,
                user_id=user_id,
                outline_raw=outline.get("raw", ""),
                created_at=now,
                updated_at=now,
            )
            session.add(creation)
            self._replace_pages(session, creation, pages)
            if task_id:
                self._upsert_task(session, task_id, record_id, RecordStatus.DRAFT, len(pages))
        return record_id

    def get_record(self, record_id: str, current_user: Optional[Dict] = None) -> Optional[Dict]:
        with get_session() as session:
            creation = session.get(Creation, record_id)
            if not creation or not self._can_access_creation(creation, current_user):
                return None
            return self._serialize_record(creation)

    def record_exists(self, record_id: str, current_user: Optional[Dict] = None) -> bool:
        with get_session() as session:
            creation = session.get(Creation, record_id)
            return creation is not None and self._can_access_creation(creation, current_user)

    def update_record(
        self,
        record_id: str,
        outline: Optional[Dict] = None,
        images: Optional[Dict] = None,
        status: Optional[str] = None,
        thumbnail: Optional[str] = None,
        content: Optional[Dict] = None,
        current_user: Optional[Dict] = None,
    ) -> bool:
        with get_session() as session:
            creation = session.get(Creation, record_id)
            if not creation or not self._can_access_creation(creation, current_user):
                return False

            if outline is not None:
                creation.outline_raw = outline.get("raw", "")
                self._replace_pages(session, creation, outline.get("pages", []))

            if images is not None:
                task_id = images.get("task_id")
                generated = images.get("generated", [])
                if task_id:
                    creation.task_id = task_id
                    self._sync_generated_slots(session, creation, task_id, generated)

            if status is not None:
                creation.status = status
                if creation.task_id:
                    self._upsert_task(
                        session,
                        creation.task_id,
                        creation.id,
                        status,
                        len(creation.pages),
                        len([img for img in creation.images if img.status == "done"]),
                        len([img for img in creation.images if img.status == "error"]),
                    )

            if thumbnail is not None:
                creation.thumbnail = thumbnail

            if content is not None:
                self.save_content(record_id, content.get("titles", []), content.get("copywriting", ""), content.get("tags", []), session=session)

            creation.updated_at = datetime.now()
            return True

    def delete_record(self, record_id: str, current_user: Optional[Dict] = None) -> bool:
        with get_session() as session:
            creation = session.get(Creation, record_id)
            if not creation or not self._can_access_creation(creation, current_user):
                return False
            task_id = creation.task_id
            session.delete(creation)

        if task_id:
            task_dir = os.path.join(self.history_dir, task_id)
            if os.path.isdir(task_dir):
                shutil.rmtree(task_dir, ignore_errors=True)
        return True

    def list_records(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        current_user: Optional[Dict] = None,
        user_id: Optional[str] = None,
    ) -> Dict:
        page = max(page, 1)
        page_size = max(page_size, 1)
        with get_session() as session:
            stmt = select(Creation)
            count_stmt = select(func.count(Creation.id))
            stmt = self._apply_user_filter(stmt, current_user)
            count_stmt = self._apply_user_filter(count_stmt, current_user)
            if user_id and current_user and current_user.get("role") == "admin":
                stmt = stmt.where(Creation.user_id == user_id)
                count_stmt = count_stmt.where(Creation.user_id == user_id)
            if status:
                if status == PUBLISHED_FILTER:
                    published_creation_ids = (
                        select(PublishDraft.creation_id)
                        .join(PublishJob, PublishJob.draft_id == PublishDraft.id)
                        .where(PublishJob.status.in_(PUBLISHED_JOB_STATUSES))
                        .distinct()
                    )
                    stmt = stmt.where(Creation.id.in_(published_creation_ids))
                    count_stmt = count_stmt.where(Creation.id.in_(published_creation_ids))
                else:
                    stmt = stmt.where(Creation.status == status)
                    count_stmt = count_stmt.where(Creation.status == status)
            total = session.scalar(count_stmt) or 0
            records = session.scalars(
                stmt.order_by(Creation.updated_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            ).all()
            published_ids = self._published_creation_ids(session, [record.id for record in records])
            return {
                "records": [self._serialize_index_record(record, record.id in published_ids) for record in records],
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size,
            }

    def search_records(self, keyword: str, current_user: Optional[Dict] = None) -> List[Dict]:
        with get_session() as session:
            stmt = self._apply_user_filter(select(Creation), current_user)
            records = session.scalars(
                stmt.where(Creation.title.ilike(f"%{keyword}%"))
                .order_by(Creation.updated_at.desc())
            ).all()
            published_ids = self._published_creation_ids(session, [record.id for record in records])
            return [self._serialize_index_record(record, record.id in published_ids) for record in records]

    def get_statistics(self, current_user: Optional[Dict] = None) -> Dict:
        with get_session() as session:
            stmt = self._apply_user_filter(select(Creation.status, func.count(Creation.id)), current_user)
            rows = session.execute(stmt.group_by(Creation.status)).all()
            by_status = {status: count for status, count in rows}
            return {"total": sum(by_status.values()), "by_status": by_status}

    def list_tasks(self, limit: int = 30, current_user: Optional[Dict] = None) -> List[Dict[str, Any]]:
        limit = max(1, min(limit, 100))
        with get_session() as session:
            stmt = (
                select(ImageTask)
                .where(ImageTask.task_id.not_like("probe_%"))
                .order_by(ImageTask.updated_at.desc())
                .limit(limit)
            )
            if current_user and current_user.get("role") != "admin":
                user_creation_ids = select(Creation.id).where(Creation.user_id == current_user.get("id"))
                stmt = stmt.where(ImageTask.creation_id.in_(user_creation_ids))
            tasks = session.scalars(stmt).all()
            results = []
            for task in tasks:
                creation = task.creation
                results.append({
                    "task_id": task.task_id,
                    "creation_id": task.creation_id,
                    "title": creation.title if creation else "未关联作品",
                    "status": task.status,
                    "total": task.total,
                    "completed": task.completed,
                    "failed": task.failed,
                    "error": task.error,
                    "created_at": task.created_at.isoformat(),
                    "updated_at": task.updated_at.isoformat(),
                    "thumbnail": creation.thumbnail if creation else None,
                })
            return results

    def delete_task(self, task_id: str) -> bool:
        with get_session() as session:
            task = session.get(ImageTask, task_id)
            session.execute(delete(GeneratedImage).where(GeneratedImage.task_id == task_id))
            if task:
                session.delete(task)
        task_dir = os.path.join(self.history_dir, task_id)
        if os.path.isdir(task_dir):
            shutil.rmtree(task_dir, ignore_errors=True)
        return True

    def save_content(
        self,
        record_id: str,
        titles: List[str],
        copywriting: str,
        tags: List[str],
        session=None,
    ) -> bool:
        def _save(active_session) -> bool:
            creation = active_session.get(Creation, record_id)
            if not creation:
                return False
            content = creation.content or GeneratedContent(creation_id=record_id)
            content.titles_json = json.dumps(titles, ensure_ascii=False)
            content.copywriting = copywriting
            content.tags_json = json.dumps(tags, ensure_ascii=False)
            content.updated_at = datetime.now()
            active_session.add(content)
            creation.updated_at = datetime.now()
            return True

        if session is not None:
            return _save(session)
        with get_session() as new_session:
            return _save(new_session)

    def find_record_id_by_task(self, task_id: str) -> Optional[str]:
        with get_session() as session:
            creation = session.scalar(select(Creation).where(Creation.task_id == task_id))
            if creation:
                return creation.id
            task = session.get(ImageTask, task_id)
            return task.creation_id if task else None

    def can_access_task(self, task_id: str, current_user: Optional[Dict]) -> bool:
        with get_session() as session:
            creation = session.scalar(select(Creation).where(Creation.task_id == task_id))
            if not creation:
                task = session.get(ImageTask, task_id)
                creation = task.creation if task else None
            return self._can_access_creation(creation, current_user)

    def mark_task_started(self, task_id: str, pages: List[Dict]) -> None:
        record_id = self.find_record_id_by_task(task_id)
        with get_session() as session:
            creation = session.get(Creation, record_id) if record_id else None
            self._upsert_task(session, task_id, record_id, RecordStatus.GENERATING, len(pages), 0, 0)
            if creation:
                creation.status = RecordStatus.GENERATING
                creation.task_id = task_id
                creation.updated_at = datetime.now()
                for page in pages:
                    self._upsert_image(session, creation, task_id, page.get("index", 0), None, "generating", None)

    def mark_image_result(self, task_id: str, page_index: int, filename: Optional[str], error: Optional[str] = None) -> None:
        record_id = self.find_record_id_by_task(task_id)
        if not record_id:
            return
        with get_session() as session:
            creation = session.get(Creation, record_id)
            if not creation:
                return
            if filename:
                self._upsert_image(session, creation, task_id, page_index, filename, "done", None)
                if not creation.thumbnail:
                    creation.thumbnail = filename
            else:
                self._upsert_image(session, creation, task_id, page_index, None, "error", error)
            self._refresh_status_from_images(session, creation, task_id)

    def scan_and_sync_task_images(self, task_id: str) -> Dict[str, Any]:
        task_dir = os.path.join(self.history_dir, task_id)
        if not os.path.isdir(task_dir):
            return {"success": False, "error": f"任务目录不存在: {task_id}"}

        image_files = self._list_task_images(task_id)
        record_id = self.find_record_id_by_task(task_id)
        if not record_id and image_files:
            record_id = self._create_orphan_task_record(task_id, image_files)

        if record_id:
            record = self.get_record(record_id)
            pages = record.get("outline", {}).get("pages", []) if record else []
            page_indices = [page.get("index", position) for position, page in enumerate(pages)]
            expected_count = len(pages) if pages else len(image_files)
            generated_slots = self._slots_from_files(image_files, page_indices or expected_count)
            status = self._status_from_counts(len([x for x in generated_slots if x]), expected_count)
            thumbnail = next((filename for filename in generated_slots if filename), None)
            self.update_record(
                record_id,
                images={"task_id": task_id, "generated": generated_slots},
                status=status,
                thumbnail=thumbnail,
            )
            return {
                "success": True,
                "record_id": record_id,
                "task_id": task_id,
                "images_count": len(image_files),
                "images": image_files,
                "status": status,
            }

        return {"success": True, "task_id": task_id, "images_count": len(image_files), "images": image_files, "no_record": True}

    def scan_all_tasks(self) -> Dict[str, Any]:
        if not os.path.isdir(self.history_dir):
            return {"success": False, "error": "历史记录目录不存在"}

        results = []
        synced_count = 0
        failed_count = 0
        orphan_tasks = []
        for item in os.listdir(self.history_dir):
            item_path = os.path.join(self.history_dir, item)
            if not os.path.isdir(item_path):
                continue
            result = self.scan_and_sync_task_images(item)
            results.append(result)
            if result.get("success"):
                if result.get("no_record"):
                    orphan_tasks.append(item)
                else:
                    synced_count += 1
            else:
                failed_count += 1
        return {
            "success": True,
            "total_tasks": len(results),
            "synced": synced_count,
            "failed": failed_count,
            "orphan_tasks": orphan_tasks,
            "results": results,
        }

    def repair_records(self, dry_run: bool = True) -> Dict[str, Any]:
        """
        修复历史记录中的常见数据不一致问题。

        当前修复项：
        - 清理挂了 task_id 但没有任何图片行的记录，避免旧任务串到新作品
        - 清理同一作品中不属于当前大纲页码的图片行
        - 按有效图片数量重算状态和缩略图
        """
        actions = []
        with get_session() as session:
            creations = session.scalars(select(Creation).order_by(Creation.updated_at.desc())).all()
            for creation in creations:
                page_indices = self._page_indices(creation)
                valid_images = [
                    image for image in creation.images
                    if image.page_index in page_indices and image.status == "done" and image.filename
                ]
                invalid_images = [
                    image for image in creation.images
                    if image.page_index not in page_indices
                ]

                if invalid_images:
                    actions.append({
                        "type": "remove_invalid_images",
                        "record_id": creation.id,
                        "title": creation.title,
                        "count": len(invalid_images),
                    })
                    if not dry_run:
                        for image in invalid_images:
                            session.delete(image)

                if creation.task_id and not creation.images:
                    actions.append({
                        "type": "clear_empty_task",
                        "record_id": creation.id,
                        "title": creation.title,
                        "task_id": creation.task_id,
                    })
                    if not dry_run:
                        creation.task_id = None
                        creation.thumbnail = None
                        if creation.status in (RecordStatus.PARTIAL, RecordStatus.COMPLETED, RecordStatus.ERROR, RecordStatus.GENERATING):
                            creation.status = RecordStatus.DRAFT
                        creation.updated_at = datetime.now()
                    continue

                if creation.images:
                    next_thumbnail = next((image.filename for image in sorted(valid_images, key=lambda img: img.page_index)), None)
                    next_status = self._status_from_counts(len(valid_images), len(creation.pages))
                    if creation.thumbnail != next_thumbnail or creation.status != next_status:
                        actions.append({
                            "type": "refresh_record_state",
                            "record_id": creation.id,
                            "title": creation.title,
                            "from_status": creation.status,
                            "to_status": next_status,
                            "from_thumbnail": creation.thumbnail,
                            "to_thumbnail": next_thumbnail,
                        })
                        if not dry_run:
                            creation.thumbnail = next_thumbnail
                            creation.status = next_status
                            creation.updated_at = datetime.now()

        return {
            "success": True,
            "dry_run": dry_run,
            "actions_count": len(actions),
            "actions": actions,
        }

    def _replace_pages(self, session, creation: Creation, pages: List[Dict]) -> None:
        session.execute(delete(OutlinePage).where(OutlinePage.creation_id == creation.id))
        session.flush()
        creation.pages.clear()
        for position, page in enumerate(pages):
            creation.pages.append(
                OutlinePage(
                    page_index=page.get("index", position),
                    type=page.get("type", "content"),
                    content=page.get("content", ""),
                )
            )

    def _sync_generated_slots(self, session, creation: Creation, task_id: str, generated: List[str]) -> None:
        page_indices = self._page_indices(creation)
        if page_indices:
            session.execute(
                delete(GeneratedImage).where(
                    GeneratedImage.creation_id == creation.id,
                    GeneratedImage.task_id == task_id,
                    GeneratedImage.page_index.not_in(page_indices),
                )
            )
        for index in page_indices:
            filename = generated[index] if index < len(generated) and generated[index] else None
            if filename:
                self._upsert_image(session, creation, task_id, index, filename, "done", None)
        done_count = len([
            index
            for index in page_indices
            if index < len(generated) and generated[index]
        ])
        self._upsert_task(session, task_id, creation.id, self._status_from_counts(done_count, len(creation.pages)), len(creation.pages), done_count, 0)

    def _upsert_image(self, session, creation: Creation, task_id: str, page_index: int, filename: Optional[str], status: str, error: Optional[str]) -> None:
        image = session.scalar(
            select(GeneratedImage).where(
                GeneratedImage.task_id == task_id,
                GeneratedImage.page_index == page_index,
            )
        )
        if not image:
            image = GeneratedImage(creation_id=creation.id, task_id=task_id, page_index=page_index)
        image.filename = filename
        image.url = f"/api/images/{task_id}/{filename}" if filename else None
        image.status = status
        image.error = error
        image.updated_at = datetime.now()
        session.add(image)

    def _upsert_task(
        self,
        session,
        task_id: str,
        creation_id: Optional[str],
        status: str,
        total: int = 0,
        completed: int = 0,
        failed: int = 0,
        error: Optional[str] = None,
    ) -> None:
        session.flush()
        task = session.get(ImageTask, task_id) or ImageTask(task_id=task_id)
        task.creation_id = creation_id or task.creation_id
        task.status = status
        task.total = total
        task.completed = completed
        task.failed = failed
        task.error = error
        task.updated_at = datetime.now()
        session.add(task)

    def _refresh_status_from_images(self, session, creation: Creation, task_id: str) -> None:
        total = len(creation.pages)
        page_indices = self._page_indices(creation)
        session.flush()
        if page_indices:
            completed = session.scalar(
                select(func.count(GeneratedImage.id)).where(
                    GeneratedImage.creation_id == creation.id,
                    GeneratedImage.task_id == task_id,
                    GeneratedImage.page_index.in_(page_indices),
                    GeneratedImage.status == "done",
                )
            ) or 0
            failed = session.scalar(
                select(func.count(GeneratedImage.id)).where(
                    GeneratedImage.creation_id == creation.id,
                    GeneratedImage.task_id == task_id,
                    GeneratedImage.page_index.in_(page_indices),
                    GeneratedImage.status == "error",
                )
            ) or 0
        else:
            completed = 0
            failed = 0
        status = RecordStatus.ERROR if failed and completed == 0 else self._status_from_counts(completed, total)
        creation.status = status
        creation.updated_at = datetime.now()
        self._upsert_task(session, task_id, creation.id, status, total, completed, failed)

    def _serialize_record(self, creation: Creation) -> Dict:
        pages = [
            {"index": page.page_index, "type": page.type, "content": page.content}
            for page in sorted(creation.pages, key=lambda p: p.page_index)
        ]
        generated = self._generated_slots(creation)
        content = self._serialize_content(creation.content)
        return {
            "id": creation.id,
            "title": creation.title,
            "user_id": creation.user_id,
            "user": self._serialize_owner(creation),
            "created_at": creation.created_at.isoformat(),
            "updated_at": creation.updated_at.isoformat(),
            "outline": {"raw": creation.outline_raw, "pages": pages},
            "images": {"task_id": creation.task_id, "generated": generated},
            "content": content,
            "status": creation.status,
            "thumbnail": creation.thumbnail,
        }

    def _serialize_index_record(self, creation: Creation, is_published: bool = False) -> Dict:
        return {
            "id": creation.id,
            "title": creation.title,
            "user_id": creation.user_id,
            "user": self._serialize_owner(creation),
            "created_at": creation.created_at.isoformat(),
            "updated_at": creation.updated_at.isoformat(),
            "status": creation.status,
            "is_published": is_published,
            "thumbnail": creation.thumbnail,
            "page_count": len(creation.pages),
            "task_id": creation.task_id,
        }

    def _serialize_owner(self, creation: Creation) -> Optional[Dict]:
        user = getattr(creation, "user", None)
        if not user:
            return None
        return {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
        }

    def _published_creation_ids(self, session, creation_ids: List[str]) -> set[str]:
        if not creation_ids:
            return set()
        rows = session.scalars(
            select(PublishDraft.creation_id)
            .join(PublishJob, PublishJob.draft_id == PublishDraft.id)
            .where(
                PublishDraft.creation_id.in_(creation_ids),
                PublishJob.status.in_(PUBLISHED_JOB_STATUSES),
            )
            .distinct()
        ).all()
        return set(rows)

    def _apply_user_filter(self, stmt, current_user: Optional[Dict]):
        if not current_user or current_user.get("role") == "admin":
            return stmt
        return stmt.where(Creation.user_id == current_user.get("id"))

    def _can_access_creation(self, creation: Optional[Creation], current_user: Optional[Dict]) -> bool:
        if not current_user:
            return True
        if current_user.get("role") == "admin":
            return True
        if not creation:
            return False
        return creation.user_id == current_user.get("id")

    def _serialize_content(self, content: Optional[GeneratedContent]) -> Optional[Dict]:
        if not content:
            return None
        try:
            titles = json.loads(content.titles_json)
        except Exception:
            titles = []
        try:
            tags = json.loads(content.tags_json)
        except Exception:
            tags = []
        return {"titles": titles, "copywriting": content.copywriting, "tags": tags, "status": "done"}

    def _generated_slots(self, creation: Creation) -> List[str]:
        page_indices = self._page_indices(creation)
        if not creation.images or not page_indices:
            return []
        max_index = max(page_indices)
        slots = [""] * (max_index + 1)
        for image in creation.images:
            if image.status == "done" and image.filename and image.page_index in page_indices:
                slots[image.page_index] = image.filename
        return slots

    def _page_indices(self, creation: Creation) -> List[int]:
        return sorted({page.page_index for page in creation.pages if page.page_index >= 0})

    def _list_task_images(self, task_id: str) -> List[str]:
        task_dir = os.path.join(self.history_dir, task_id)
        if not os.path.isdir(task_dir):
            return []
        files = [
            filename
            for filename in os.listdir(task_dir)
            if not filename.startswith("thumb_") and filename.lower().endswith((".png", ".jpg", ".jpeg"))
        ]
        files.sort(key=lambda filename: self._filename_index(filename))
        return files

    def _slots_from_files(self, image_files: List[str], expected_pages) -> List[str]:
        if isinstance(expected_pages, int):
            page_indices = list(range(expected_pages))
        else:
            page_indices = sorted({index for index in expected_pages if index >= 0})
        if not page_indices:
            return []
        page_count = max(page_indices) + 1
        slots = [""] * page_count
        for filename in image_files:
            index = self._filename_index(filename)
            if index in page_indices:
                slots[index] = filename
        return slots

    def _create_orphan_task_record(self, task_id: str, image_files: List[str]) -> str:
        page_count = max([self._filename_index(name) for name in image_files] + [-1]) + 1 or len(image_files)
        pages = [
            {
                "index": index,
                "type": "cover" if index == 0 else "content",
                "content": "该页面由历史图片任务恢复，原始大纲未关联。",
            }
            for index in range(page_count)
        ]
        record_id = self.create_record(
            topic=f"恢复的图片任务（{len(image_files)}张）",
            outline={"raw": "该记录由孤立图片任务自动恢复，原始大纲未关联。", "pages": pages},
            task_id=task_id,
        )
        generated_slots = self._slots_from_files(image_files, page_count)
        self.update_record(
            record_id,
            images={"task_id": task_id, "generated": generated_slots},
            status=self._status_from_counts(len([x for x in generated_slots if x]), page_count),
            thumbnail=next((filename for filename in generated_slots if filename), None),
        )
        return record_id

    def _status_from_counts(self, completed: int, total: int) -> str:
        if completed <= 0:
            return RecordStatus.DRAFT
        if total and completed >= total:
            return RecordStatus.COMPLETED
        return RecordStatus.PARTIAL

    def _filename_index(self, filename: str) -> int:
        try:
            return int(os.path.splitext(filename)[0])
        except Exception:
            return 999999


_service_instance = None


def get_history_service() -> HistoryService:
    global _service_instance
    if _service_instance is None:
        _service_instance = HistoryService()
    return _service_instance
