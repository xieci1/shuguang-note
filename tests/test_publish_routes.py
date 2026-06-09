def _register(client, name, email):
    response = client.post("/api/auth/register", json={
        "name": name,
        "email": email,
        "password": "secret123",
    })
    assert response.status_code == 200
    data = response.get_json()
    return data["user"], {"Authorization": f"Bearer {data['token']}"}


def test_publish_accounts_api(isolated_history_service, tmp_path, monkeypatch):
    from backend import db
    from flask import Flask
    from backend.routes.publish_routes import create_publish_blueprint
    from backend.routes.user_routes import create_user_blueprint
    from backend.services import history as history_module
    from backend.services import publish as publish_module
    from backend.services import users as users_module

    monkeypatch.setattr(history_module, "_service_instance", isolated_history_service)
    monkeypatch.setattr(publish_module, "_service_instance", None)
    monkeypatch.setattr(users_module, "_service_instance", None)
    app = Flask(__name__)
    app.register_blueprint(create_user_blueprint(), url_prefix="/api")
    app.register_blueprint(create_publish_blueprint(), url_prefix="/api")
    app.config["TESTING"] = True
    client = app.test_client()

    service = publish_module.get_publish_service()
    service.profile_root = tmp_path / "profiles"
    service.config_path = tmp_path / "missing_publish_providers.yaml"

    _admin, admin_headers = _register(client, "管理员", "admin@example.com")
    member, member_headers = _register(client, "成员", "member@example.com")

    response = client.post("/api/publish/accounts", json={
        "name": "主账号",
        "platform": "xhs",
    }, headers=admin_headers)
    assert response.status_code == 200
    admin_account_id = response.get_json()["account_id"]

    response = client.post("/api/publish/accounts", json={
        "name": "主账号",
        "platform": "xhs",
    }, headers=member_headers)
    assert response.status_code == 200
    member_account_id = response.get_json()["account_id"]

    response = client.get("/api/publish/accounts?platform=xhs", headers=member_headers)
    data = response.get_json()
    assert data["success"] is True
    assert [account["id"] for account in data["accounts"]] == [member_account_id]
    assert data["accounts"][0]["user_id"] == member["id"]

    response = client.get("/api/publish/accounts?platform=xhs", headers=admin_headers)
    data = response.get_json()
    assert {account["id"] for account in data["accounts"]} == {admin_account_id, member_account_id}

    forbidden = client.post(f"/api/publish/accounts/{admin_account_id}/login", json={}, headers=member_headers)
    assert forbidden.status_code == 400
    assert "无权" in forbidden.get_json()["error"]

    response = client.post(f"/api/publish/accounts/{member_account_id}/login", json={}, headers=member_headers)
    assert response.status_code == 400
    assert "未配置" in response.get_json()["error"]

    db.engine.dispose()


def test_publish_draft_can_select_pages(isolated_history_service, tmp_path, monkeypatch):
    import json
    from flask import Flask
    from backend import db
    from backend.routes.publish_routes import create_publish_blueprint
    from backend.routes.user_routes import create_user_blueprint
    from backend.services import history as history_module
    from backend.services import publish as publish_module
    from backend.services import users as users_module
    from backend.db import get_session
    from backend.models import PublishDraft

    monkeypatch.setattr(history_module, "_service_instance", isolated_history_service)
    monkeypatch.setattr(publish_module, "_service_instance", None)
    monkeypatch.setattr(users_module, "_service_instance", None)

    app = Flask(__name__)
    app.register_blueprint(create_user_blueprint(), url_prefix="/api")
    app.register_blueprint(create_publish_blueprint(), url_prefix="/api")
    app.config["TESTING"] = True
    client = app.test_client()

    service = publish_module.get_publish_service()
    service.profile_root = tmp_path / "profiles"
    service.config_path = tmp_path / "missing_publish_providers.yaml"

    _admin, headers = _register(client, "管理员", "admin-select@example.com")
    account = client.post("/api/publish/accounts", json={"name": "发布账号"}, headers=headers)
    account_id = account.get_json()["account_id"]

    task_id = "task_select_pages"
    task_dir = tmp_path / "history" / task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    for index in range(4):
        (task_dir / f"{index}.png").write_bytes(b"png")

    record_id = isolated_history_service.create_record(
        topic="选择发布图片",
        outline={
            "raw": "test",
            "pages": [
                {"index": 0, "type": "cover", "content": "P1"},
                {"index": 1, "type": "content", "content": "P2"},
                {"index": 2, "type": "content", "content": "P3"},
                {"index": 3, "type": "summary", "content": "P4"},
            ],
        },
    )
    isolated_history_service.update_record(
        record_id,
        images={"task_id": task_id, "generated": ["0.png", "1.png", "2.png", "3.png"]},
        status="completed",
        thumbnail="0.png",
    )

    response = client.post("/api/publish/drafts", json={
        "creation_id": record_id,
        "account_id": account_id,
        "title": "只发两张",
        "body": "正文",
        "tags": ["测试"],
        "page_indexes": [0, 2],
    }, headers=headers)
    assert response.status_code == 200
    draft_id = response.get_json()["draft_id"]

    with get_session() as session:
        draft = session.get(PublishDraft, draft_id)
        media = json.loads(draft.media_json)

    assert [item["page_index"] for item in media] == [0, 2]
    assert [item["filename"] for item in media] == ["0.png", "2.png"]

    db.engine.dispose()
