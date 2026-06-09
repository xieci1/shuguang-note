import json


def test_migrate_record_imports_legacy_json(
    isolated_history_service,
    sample_outline,
    tmp_path,
    monkeypatch,
):
    from backend.services import history as history_module
    from scripts import migrate_history_to_db

    monkeypatch.setattr(history_module, "_service_instance", isolated_history_service)

    history_dir = tmp_path / "legacy_history"
    history_dir.mkdir()
    task_dir = history_dir / "task_legacy"
    task_dir.mkdir()
    (task_dir / "0.png").write_bytes(b"fake image")
    (task_dir / "thumb_0.png").write_bytes(b"fake thumbnail")

    monkeypatch.setattr(migrate_history_to_db, "HISTORY_DIR", history_dir)

    record = {
        "id": "legacy-record-1",
        "title": "旧记录",
        "status": "completed",
        "outline": sample_outline,
        "images": {
            "task_id": "task_legacy",
            "generated": ["0.png"],
        },
        "content": {
            "titles": ["旧标题"],
            "copywriting": "旧正文",
            "tags": ["旧标签"],
        },
        "thumbnail": "0.png",
        "created_at": "2026-06-01T10:00:00",
        "updated_at": "2026-06-01T11:00:00",
    }
    (history_dir / "legacy-record-1.json").write_text(
        json.dumps(record, ensure_ascii=False),
        encoding="utf-8",
    )

    assert migrate_history_to_db.main() == 0
    assert migrate_history_to_db.main() == 0

    imported = isolated_history_service.get_record("legacy-record-1")
    assert imported["title"] == "旧记录"
    assert imported["outline"]["pages"] == sample_outline["pages"]
    assert imported["images"]["task_id"] == "task_legacy"
    assert imported["images"]["generated"][0] == "0.png"
    assert imported["content"]["titles"] == ["旧标题"]

