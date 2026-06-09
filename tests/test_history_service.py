from pathlib import Path
from datetime import datetime

from backend.db import get_session
from backend.models import PublishAccount, PublishDraft, PublishJob

def test_history_service_crud_and_content(isolated_history_service, sample_outline):
    service = isolated_history_service

    record_id = service.create_record("秋季穿搭指南", sample_outline)
    record = service.get_record(record_id)

    assert record["title"] == "秋季穿搭指南"
    assert record["status"] == "draft"
    assert record["outline"]["pages"][0]["type"] == "cover"
    assert record["images"] == {"task_id": None, "generated": []}

    updated_outline = {
        "raw": "新版大纲",
        "pages": [
            {"index": 0, "type": "cover", "content": "新版封面"},
            {"index": 1, "type": "summary", "content": "新版总结"},
        ],
    }
    assert service.update_record(
        record_id,
        outline=updated_outline,
        content={
            "titles": ["标题 A", "标题 B"],
            "copywriting": "正文内容",
            "tags": ["穿搭", "秋季"],
        },
    )

    record = service.get_record(record_id)
    assert record["outline"] == updated_outline
    assert record["content"]["titles"] == ["标题 A", "标题 B"]
    assert record["content"]["copywriting"] == "正文内容"
    assert record["content"]["tags"] == ["穿搭", "秋季"]

    listed = service.list_records()
    assert listed["total"] == 1
    assert listed["records"][0]["id"] == record_id

    assert service.search_records("秋季")[0]["id"] == record_id
    assert service.record_exists(record_id)
    assert service.delete_record(record_id)
    assert not service.record_exists(record_id)


def test_image_task_state_is_synced_to_record(isolated_history_service, sample_outline):
    service = isolated_history_service
    task_id = "task_unit_sync"
    record_id = service.create_record("图片任务", sample_outline, task_id=task_id)

    service.mark_task_started(task_id, sample_outline["pages"])
    service.mark_image_result(task_id, 0, "0.png")
    service.mark_image_result(task_id, 1, None, "timeout")

    record = service.get_record(record_id)
    assert record["status"] == "partial"
    assert record["thumbnail"] == "0.png"
    assert record["images"]["generated"][0] == "0.png"

    tasks = service.list_tasks()
    assert tasks[0]["task_id"] == task_id
    assert tasks[0]["completed"] == 1
    assert tasks[0]["failed"] == 1


def test_scan_orphan_task_creates_recovered_record(isolated_history_service):
    service = isolated_history_service
    task_id = "task_orphan"
    task_dir = Path(service.history_dir) / task_id
    task_dir.mkdir()
    (task_dir / "0.png").write_bytes(b"fake image")
    (task_dir / "thumb_0.png").write_bytes(b"fake thumbnail")
    (task_dir / "1.png").write_bytes(b"fake image")

    result = service.scan_and_sync_task_images(task_id)

    assert result["success"] is True
    assert result["images_count"] == 2
    assert result["status"] == "completed"

    record = service.get_record(result["record_id"])
    assert record["title"] == "恢复的图片任务（2张）"
    assert record["images"]["generated"] == ["0.png", "1.png"]


def test_delete_task_removes_images_and_files(isolated_history_service, sample_outline):
    service = isolated_history_service
    task_id = "task_delete"
    record_id = service.create_record("删除任务", sample_outline, task_id=task_id)
    service.mark_task_started(task_id, sample_outline["pages"])
    service.mark_image_result(task_id, 0, "0.png")

    task_dir = Path(service.history_dir) / task_id
    task_dir.mkdir(exist_ok=True)
    (task_dir / "0.png").write_bytes(b"fake image")

    assert service.delete_task(task_id)
    assert not task_dir.exists()

    record = service.get_record(record_id)
    assert record is not None
    assert record["images"]["generated"] == []


def test_list_records_can_filter_published_creations(isolated_history_service, sample_outline):
    service = isolated_history_service
    published_id = service.create_record("已发布作品", sample_outline)
    draft_id = service.create_record("未发布作品", sample_outline)
    now = datetime.now()

    with get_session() as session:
        account = PublishAccount(
            id="account-published",
            platform="xhs",
            name="主账号",
            profile_dir="profiles/account-published",
            created_at=now,
            updated_at=now,
        )
        publish_draft = PublishDraft(
            id="draft-published",
            creation_id=published_id,
            account_id=account.id,
            platform="xhs",
            title="标题",
            body="正文",
            created_at=now,
            updated_at=now,
        )
        job = PublishJob(
            id="job-published",
            draft_id=publish_draft.id,
            account_id=account.id,
            platform="xhs",
            status="ready_for_review",
            created_at=now,
            updated_at=now,
        )
        session.add_all([account, publish_draft, job])

    result = service.list_records(status="published")

    assert result["total"] == 1
    assert result["records"][0]["id"] == published_id
    assert result["records"][0]["id"] != draft_id
    assert result["records"][0]["is_published"] is True

    all_records = service.list_records()
    by_id = {record["id"]: record for record in all_records["records"]}
    assert by_id[published_id]["is_published"] is True
    assert by_id[draft_id]["is_published"] is False
