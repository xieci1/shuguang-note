from flask import Flask


def _register(client, name, email):
    response = client.post("/api/auth/register", json={
        "name": name,
        "email": email,
        "password": "secret123",
    })
    assert response.status_code == 200
    data = response.get_json()
    return data["user"], {"Authorization": f"Bearer {data['token']}"}


class FakeImageService:
    def generate_images(self, pages, task_id, full_outline, user_images=None, user_topic="", quality_mode="fast"):
        yield {
            "event": "finish",
            "data": {
                "success": True,
                "task_id": task_id or "task_quota",
                "completed": 0,
                "failed": 0,
            },
        }


def test_member_image_generation_quota(isolated_history_service, monkeypatch, sample_outline):
    from backend.routes.image_routes import create_image_blueprint
    from backend.routes.user_routes import create_user_blueprint
    from backend.services import history as history_module
    from backend.services import image as image_module
    from backend.services import users as users_module

    monkeypatch.setattr(history_module, "_service_instance", isolated_history_service)
    monkeypatch.setattr(users_module, "_service_instance", None)
    monkeypatch.setattr(image_module, "get_image_service", lambda: FakeImageService())

    app = Flask(__name__)
    app.register_blueprint(create_user_blueprint(), url_prefix="/api")
    app.register_blueprint(create_image_blueprint(), url_prefix="/api")
    app.config["TESTING"] = True
    client = app.test_client()

    _admin, admin_headers = _register(client, "管理员", "admin@example.com")
    member, member_headers = _register(client, "成员", "member@example.com")

    response = client.put(f"/api/users/{member['id']}", json={"quota_limit": 1}, headers=admin_headers)
    assert response.status_code == 200
    assert response.get_json()["user"]["quota_remaining"] == 1

    record_id = isolated_history_service.create_record(
        "额度测试",
        sample_outline,
        task_id="task_quota",
        user_id=member["id"],
    )
    assert record_id

    response = client.post("/api/generate", json={
        "task_id": "task_quota",
        "pages": sample_outline["pages"][:2],
    }, headers=member_headers)
    assert response.status_code == 403
    assert "生成额度不足" in response.get_json()["error"]

    response = client.post("/api/generate", json={
        "task_id": "task_quota",
        "pages": sample_outline["pages"][:1],
    }, headers=member_headers)
    assert response.status_code == 200
    assert b"event: finish" in response.data

    users = client.get("/api/users", headers=admin_headers).get_json()["users"]
    updated_member = next(user for user in users if user["id"] == member["id"])
    assert updated_member["quota_used"] == 1
    assert updated_member["quota_remaining"] == 0
