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


def test_history_routes_filter_by_user(isolated_history_service, monkeypatch, sample_outline):
    from backend.routes.history_routes import create_history_blueprint
    from backend.routes.user_routes import create_user_blueprint
    from backend.services import history as history_module
    from backend.services import users as users_module

    monkeypatch.setattr(history_module, "_service_instance", isolated_history_service)
    monkeypatch.setattr(users_module, "_service_instance", None)

    app = Flask(__name__)
    app.register_blueprint(create_user_blueprint(), url_prefix="/api")
    app.register_blueprint(create_history_blueprint(), url_prefix="/api")
    app.config["TESTING"] = True
    client = app.test_client()

    admin, admin_headers = _register(client, "管理员", "admin@example.com")
    member, member_headers = _register(client, "成员", "member@example.com")

    response = client.post("/api/history", json={
        "topic": "管理员作品",
        "outline": sample_outline,
    }, headers=admin_headers)
    assert response.status_code == 200
    admin_record_id = response.get_json()["record_id"]

    response = client.post("/api/history", json={
        "topic": "成员作品",
        "outline": sample_outline,
    }, headers=member_headers)
    assert response.status_code == 200
    member_record_id = response.get_json()["record_id"]

    member_list = client.get("/api/history", headers=member_headers).get_json()
    assert [record["id"] for record in member_list["records"]] == [member_record_id]
    assert member_list["records"][0]["user"]["name"] == "成员"

    admin_list = client.get("/api/history", headers=admin_headers).get_json()
    assert {record["id"] for record in admin_list["records"]} == {admin_record_id, member_record_id}
    owners = {record["id"]: record["user"]["email"] for record in admin_list["records"]}
    assert owners[admin_record_id] == "admin@example.com"
    assert owners[member_record_id] == "member@example.com"

    admin_filtered = client.get(f"/api/history?user_id={member['id']}", headers=admin_headers).get_json()
    assert [record["id"] for record in admin_filtered["records"]] == [member_record_id]

    member_ignored_filter = client.get(f"/api/history?user_id={admin['id']}", headers=member_headers).get_json()
    assert [record["id"] for record in member_ignored_filter["records"]] == [member_record_id]

    forbidden = client.get(f"/api/history/{admin_record_id}", headers=member_headers)
    assert forbidden.status_code == 404

    assert admin["role"] == "admin"
    assert member["role"] == "member"
