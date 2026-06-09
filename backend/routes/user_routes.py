"""用户管理 API 路由。"""

from flask import Blueprint, jsonify, request

from backend.auth import get_current_user, require_admin, require_user
from backend.services.users import get_user_service


def create_user_blueprint():
    user_bp = Blueprint("users", __name__)

    @user_bp.route("/users", methods=["GET"])
    @require_admin()
    def list_users(_current_user):
        return jsonify({
            "success": True,
            "users": get_user_service().list_users(),
        }), 200

    @user_bp.route("/users", methods=["POST"])
    @require_admin()
    def create_user(_current_user):
        try:
            data = request.get_json(silent=True) or {}
            user_id = get_user_service().create_user(
                name=data.get("name") or "",
                email=data.get("email") or "",
                role=data.get("role") or "member",
                password=data.get("password") or None,
                quota_limit=data.get("quota_limit"),
            )
            return jsonify({"success": True, "user_id": user_id}), 200
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 400

    @user_bp.route("/users/<user_id>", methods=["PUT"])
    @require_admin()
    def update_user(_current_user, user_id):
        try:
            data = request.get_json(silent=True) or {}
            user = get_user_service().update_user(user_id, data)
            if not user:
                return jsonify({"success": False, "error": "用户不存在"}), 404
            return jsonify({"success": True, "user": user}), 200
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 400

    @user_bp.route("/users/<user_id>", methods=["DELETE"])
    @require_admin()
    def delete_user(_current_user, user_id):
        success = get_user_service().delete_user(user_id)
        if not success:
            return jsonify({"success": False, "error": "用户不存在"}), 404
        return jsonify({"success": True}), 200

    @user_bp.route("/auth/register", methods=["POST"])
    def register():
        try:
            data = request.get_json(silent=True) or {}
            result = get_user_service().register(
                name=data.get("name") or "",
                email=data.get("email") or "",
                password=data.get("password") or "",
            )
            return jsonify({"success": True, **result}), 200
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 400

    @user_bp.route("/auth/login", methods=["POST"])
    def login():
        try:
            data = request.get_json(silent=True) or {}
            result = get_user_service().login(
                identifier=data.get("email") or data.get("identifier") or "",
                password=data.get("password") or "",
            )
            return jsonify({"success": True, **result}), 200
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 400

    @user_bp.route("/auth/me", methods=["GET"])
    @require_user()
    def me(current_user):
        return jsonify({"success": True, "user": current_user}), 200

    @user_bp.route("/auth/logout", methods=["POST"])
    def logout():
        auth_header = request.headers.get("Authorization", "")
        if auth_header.lower().startswith("bearer "):
            get_user_service().logout(auth_header[7:].strip())
        return jsonify({"success": True}), 200

    return user_bp
