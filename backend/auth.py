"""请求认证辅助函数。"""

from __future__ import annotations

from functools import wraps

from flask import jsonify, request

from backend.services.users import get_user_service


def get_current_user() -> dict | None:
    auth_header = request.headers.get("Authorization", "")
    token = ""
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()
    if not token:
        token = request.args.get("access_token", "").strip()
    return get_user_service().current_user(token)


def require_user():
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user = get_current_user()
            if not user:
                return jsonify({"success": False, "error": "请先登录"}), 401
            return func(user, *args, **kwargs)
        return wrapper
    return decorator


def require_admin():
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user = get_current_user()
            if not user:
                return jsonify({"success": False, "error": "请先登录"}), 401
            if user.get("role") != "admin":
                return jsonify({"success": False, "error": "需要管理员权限"}), 403
            return func(user, *args, **kwargs)
        return wrapper
    return decorator
