from flask import Flask


def test_user_management_api(isolated_history_service, monkeypatch):
    from backend import db
    from backend.routes.user_routes import create_user_blueprint
    from backend.services import users as users_module

    monkeypatch.setattr(users_module, "_service_instance", None)

    app = Flask(__name__)
    app.register_blueprint(create_user_blueprint(), url_prefix="/api")
    app.config["TESTING"] = True
    client = app.test_client()

    response = client.post("/api/auth/register", json={
        "name": "管理员",
        "email": "admin@example.com",
        "password": "secret123",
    })
    assert response.status_code == 200
    admin_data = response.get_json()
    admin_token = admin_data["token"]
    assert admin_data["user"]["role"] == "admin"
    assert admin_data["user"]["quota_limit"] is None
    headers = {"Authorization": f"Bearer {admin_token}"}

    response = client.post("/api/auth/register", json={
        "name": "普通成员",
        "email": "member@example.com",
        "password": "secret123",
    })
    assert response.status_code == 200
    member_data = response.get_json()
    assert member_data["user"]["role"] == "member"
    assert member_data["user"]["quota_limit"] == 6
    assert member_data["user"]["quota_remaining"] == 6

    response = client.post("/api/users", json={
        "name": "运营同学",
        "email": "editor@example.com",
        "role": "editor",
        "password": "secret456",
    }, headers=headers)
    assert response.status_code == 200
    user_id = response.get_json()["user_id"]

    response = client.get("/api/users", headers=headers)
    data = response.get_json()
    assert data["success"] is True
    assert data["users"][0]["id"] == user_id
    assert data["users"][0]["role"] == "editor"
    assert data["users"][0]["quota_limit"] == 6
    assert data["users"][0]["quota_remaining"] == 6

    response = client.put(f"/api/users/{user_id}", json={"status": "disabled"}, headers=headers)
    assert response.status_code == 200
    assert response.get_json()["user"]["status"] == "disabled"

    response = client.delete(f"/api/users/{user_id}", headers=headers)
    assert response.status_code == 200

    response = client.get("/api/users", headers=headers)
    assert len(response.get_json()["users"]) == 2

    login = client.post("/api/auth/login", json={
        "email": "admin@example.com",
        "password": "secret123",
    })
    assert login.status_code == 200
    assert login.get_json()["user"]["role"] == "admin"

    login_by_name = client.post("/api/auth/login", json={
        "email": "管理员",
        "password": "secret123",
    })
    assert login_by_name.status_code == 200
    assert login_by_name.get_json()["user"]["email"] == "admin@example.com"

    monkeypatch.setattr(users_module, "_service_instance", None)
    db.engine.dispose()
