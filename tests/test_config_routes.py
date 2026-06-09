from flask import Flask


def _register(client, name, email):
    response = client.post("/api/auth/register", json={
        "name": name,
        "email": email,
        "password": "secret123",
    })
    assert response.status_code == 200
    data = response.get_json()
    return {"Authorization": f"Bearer {data['token']}"}


def test_config_routes_require_admin(isolated_history_service, monkeypatch):
    from backend.routes.config_routes import create_config_blueprint
    from backend.routes.user_routes import create_user_blueprint
    from backend.services import users as users_module

    monkeypatch.setattr(users_module, "_service_instance", None)

    app = Flask(__name__)
    app.register_blueprint(create_user_blueprint(), url_prefix="/api")
    app.register_blueprint(create_config_blueprint(), url_prefix="/api")
    app.config["TESTING"] = True
    client = app.test_client()

    admin_headers = _register(client, "管理员", "admin@example.com")
    member_headers = _register(client, "成员", "member@example.com")

    anonymous = client.get("/api/config")
    assert anonymous.status_code == 401

    forbidden = client.get("/api/config", headers=member_headers)
    assert forbidden.status_code == 403
    assert forbidden.get_json()["error"] == "需要管理员权限"

    allowed = client.get("/api/config", headers=admin_headers)
    assert allowed.status_code == 200
    assert allowed.get_json()["success"] is True
