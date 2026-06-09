import json
import subprocess
import time
from pathlib import Path

from backend.models import PublishDraft


def _make_completed_creation(service, sample_outline):
    task_id = "task_publish"
    record_id = service.create_record("发布测试", sample_outline, task_id=task_id)
    service.mark_task_started(task_id, sample_outline["pages"])
    task_dir = Path(service.history_dir) / task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "0.png").write_bytes(b"fake image")
    service.mark_image_result(task_id, 0, "0.png")
    return record_id


def test_publish_account_crud(tmp_path, monkeypatch):
    from backend.db import get_session
    from backend.services import publish as publish_module
    from backend import db

    db.configure_database(f"sqlite:///{tmp_path / 'publish.sqlite3'}")
    db.init_db()
    monkeypatch.setattr(publish_module, "_service_instance", None)

    service = publish_module.PublishService()
    service.profile_root = tmp_path / "profiles"
    user_a = {"id": "user-a", "role": "member"}
    user_b = {"id": "user-b", "role": "member"}
    admin = {"id": "admin", "role": "admin"}
    account_id = service.create_account("主账号", "xhs", current_user=user_a)
    other_account_id = service.create_account("主账号", "xhs", current_user=user_b)

    accounts = service.list_accounts("xhs", current_user=user_a)
    assert accounts[0]["id"] == account_id
    assert accounts[0]["platform"] == "xhs"
    assert Path(accounts[0]["profile_dir"]).exists()
    assert [account["id"] for account in service.list_accounts("xhs", current_user=user_b)] == [other_account_id]
    assert {account["id"] for account in service.list_accounts("xhs", current_user=admin)} == {account_id, other_account_id}

    try:
        service.create_account("主账号", "xhs", current_user=user_a)
        assert False, "同平台同名账号不应重复创建"
    except ValueError as exc:
        assert "同名" in str(exc)

    assert service.delete_account(account_id, current_user=user_a)
    assert service.list_accounts("xhs", current_user=user_a) == []


def test_create_publish_draft_validates_images(
    isolated_history_service,
    sample_outline,
    tmp_path,
    monkeypatch,
):
    from backend.db import get_session
    from backend.services import publish as publish_module
    from backend.services import history as history_module

    monkeypatch.setattr(history_module, "_service_instance", isolated_history_service)
    monkeypatch.setattr(publish_module, "_service_instance", None)

    service = publish_module.PublishService()
    service.profile_root = tmp_path / "profiles"
    account_id = service.create_account("主账号", "xhs")
    record_id = isolated_history_service.create_record("无图记录", sample_outline)

    try:
        service.create_draft(record_id, account_id, "标题", "正文", ["标签"])
        assert False, "无图片记录不应创建发布草稿"
    except ValueError as exc:
        assert "没有可发布" in str(exc)

    record_id = _make_completed_creation(isolated_history_service, sample_outline)
    draft_id = service.create_draft(record_id, account_id, "标题", "正文", ["标签"])

    with get_session() as session:
        draft = session.get(PublishDraft, draft_id)
        media = json.loads(draft.media_json)
        assert draft.title == "标题"
        assert media[0]["filename"] == "0.png"
        assert Path(media[0]["path"]).exists()


def test_publish_job_success_with_cli(
    isolated_history_service,
    sample_outline,
    tmp_path,
    monkeypatch,
):
    from backend.services import publish as publish_module
    from backend.services import history as history_module

    monkeypatch.setattr(history_module, "_service_instance", isolated_history_service)
    monkeypatch.setattr(publish_module, "_service_instance", None)

    wrapper = tmp_path / "fake_publish.py"
    wrapper.write_text(
        "import json, sys\n"
        "payload=json.load(open(sys.argv[-1], encoding='utf-8'))\n"
        "assert payload['post']['click_publish'] is True\n"
        "print(json.dumps({'success': True, 'message': 'ready'}))\n",
        encoding="utf-8",
    )
    config = tmp_path / "publish_providers.yaml"
    config.write_text(
        "platforms:\n"
        "  xhs:\n"
        "    enabled: true\n"
        f"    command: ['python', '{wrapper.as_posix()}']\n"
        f"    working_dir: '{tmp_path.as_posix()}'\n",
        encoding="utf-8",
    )

    service = publish_module.PublishService()
    service.profile_root = tmp_path / "profiles"
    service.config_path = config
    account_id = service.create_account("主账号", "xhs")
    record_id = _make_completed_creation(isolated_history_service, sample_outline)
    draft_id = service.create_draft(record_id, account_id, "标题", "正文", ["标签"])

    result = service.run_draft(draft_id)
    assert result["success"] is True
    job_id = result["job_id"]

    deadline = time.time() + 5
    job = service.get_job(job_id)
    while job["status"] in ("queued", "running") and time.time() < deadline:
        time.sleep(0.05)
        job = service.get_job(job_id)

    assert job["status"] == "ready_for_review"
    assert job["account_name"] == "主账号"
    assert job["draft_title"] == "标题"
    assert "ready" in job["logs"]

    jobs = service.list_jobs()
    assert jobs[0]["id"] == job_id


def test_publish_job_failure_when_cli_missing(
    isolated_history_service,
    sample_outline,
    tmp_path,
    monkeypatch,
):
    from backend.services import publish as publish_module
    from backend.services import history as history_module

    monkeypatch.setattr(history_module, "_service_instance", isolated_history_service)
    monkeypatch.setattr(publish_module, "_service_instance", None)

    service = publish_module.PublishService()
    service.profile_root = tmp_path / "profiles"
    service.config_path = tmp_path / "missing_publish_providers.yaml"
    account_id = service.create_account("主账号", "xhs")
    record_id = _make_completed_creation(isolated_history_service, sample_outline)
    draft_id = service.create_draft(record_id, account_id, "标题", "正文", ["标签"])

    result = service.run_draft(draft_id)
    job_id = result["job_id"]

    deadline = time.time() + 5
    job = service.get_job(job_id)
    while job["status"] in ("queued", "running") and time.time() < deadline:
        time.sleep(0.05)
        job = service.get_job(job_id)

    assert job["status"] == "failed"
    assert "未配置" in job["error"]


def test_xhs_wrapper_direct_publish_deduplicates_images(tmp_path, monkeypatch):
    import scripts.xhs_sau_wrapper as wrapper

    payload = tmp_path / "payload.json"
    image = tmp_path / "0.png"
    image.write_bytes(b"fake")
    payload.write_text(
        json.dumps({
            "account": {"name": "主账号"},
            "post": {
                "title": "标题",
                "body": "正文",
                "tags": ["标签"],
                "media": [{"path": str(image)}, {"path": str(image)}],
                "click_publish": True,
            },
        }, ensure_ascii=False),
        encoding="utf-8",
    )

    calls = []

    class FakeCompleted:
        returncode = 0
        stdout = "ok"
        stderr = ""

    def fake_run(command, env=None, **kwargs):
        calls.append((command, env))
        return FakeCompleted()

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setenv("SAU_BIN", "sau-test")
    monkeypatch.setenv("SHUGUANG_NOTE_ALLOW_DIRECT_PUBLISH", "true")
    monkeypatch.setattr("sys.argv", ["xhs_sau_wrapper.py", str(payload)])

    assert wrapper.main() == 0
    command, env = calls[0]
    assert command[:3] == ["sau-test", "xiaohongshu", "upload-note"]
    assert "--tags" in command
    assert command.count(str(image)) == 1
