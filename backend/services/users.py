"""用户管理服务。"""

from __future__ import annotations

import re
import secrets
from datetime import datetime, timedelta
from hashlib import sha256
from uuid import uuid4

from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy import func, select

from backend.db import get_session
from backend.models import User, UserSession


VALID_ROLES = {"admin", "editor", "member"}
VALID_STATUSES = {"active", "disabled"}
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
SESSION_DAYS = 14
DEFAULT_REGISTER_MEMBER_QUOTA = 6


class UserService:
    def list_users(self) -> list[dict]:
        with get_session() as session:
            users = session.scalars(select(User).order_by(User.created_at.desc())).all()
            return [self._serialize_user(user) for user in users]

    def create_user(
        self,
        name: str,
        email: str,
        role: str = "member",
        password: str | None = None,
        quota_limit: int | None = None,
    ) -> str:
        name = self._normalize_name(name)
        email = self._normalize_email(email)
        role = self._normalize_role(role)
        password_hash = generate_password_hash(self._normalize_password(password or secrets.token_urlsafe(12)))

        with get_session() as session:
            existing = session.scalar(select(User).where(User.email == email))
            if existing:
                raise ValueError("邮箱已存在")

            user = User(
                id=uuid4().hex,
                name=name,
                email=email,
                password_hash=password_hash,
                role=role,
                status="active",
                quota_limit=self._default_quota_limit_for_role(role) if quota_limit is None else self._normalize_quota_limit(quota_limit),
                quota_used=0,
            )
            session.add(user)
            return user.id

    def update_user(self, user_id: str, data: dict) -> dict | None:
        with get_session() as session:
            user = session.get(User, user_id)
            if not user:
                return None

            if "name" in data:
                user.name = self._normalize_name(data.get("name") or "")
            if "email" in data:
                email = self._normalize_email(data.get("email") or "")
                existing = session.scalar(select(User).where(User.email == email, User.id != user_id))
                if existing:
                    raise ValueError("邮箱已存在")
                user.email = email
            if "role" in data:
                user.role = self._normalize_role(data.get("role") or "")
            if "status" in data:
                user.status = self._normalize_status(data.get("status") or "")
            if "password" in data and data.get("password"):
                user.password_hash = generate_password_hash(self._normalize_password(data.get("password") or ""))
            if "quota_limit" in data:
                user.quota_limit = self._normalize_quota_limit(data.get("quota_limit"))
            if "quota_used" in data:
                user.quota_used = self._normalize_quota_used(data.get("quota_used"))

            user.updated_at = datetime.now()
            session.flush()
            return self._serialize_user(user)

    def consume_quota(self, user_id: str, amount: int) -> dict:
        amount = max(0, int(amount or 0))
        with get_session() as session:
            user = session.get(User, user_id)
            if not user:
                raise ValueError("用户不存在")
            if user.role == "admin" or amount == 0:
                return self._serialize_user(user)

            limit = user.quota_limit
            used = user.quota_used or 0
            if limit is not None and used + amount > limit:
                remaining = max(limit - used, 0)
                raise ValueError(f"生成额度不足，剩余额度 {remaining} 张，本次需要 {amount} 张")

            user.quota_used = used + amount
            user.updated_at = datetime.now()
            session.flush()
            return self._serialize_user(user)

    def delete_user(self, user_id: str) -> bool:
        with get_session() as session:
            user = session.get(User, user_id)
            if not user:
                return False
            session.delete(user)
            return True

    def register(self, name: str, email: str, password: str) -> dict:
        name = self._normalize_name(name)
        email = self._normalize_email(email)
        password_hash = generate_password_hash(self._normalize_password(password))

        with get_session() as session:
            existing = session.scalar(select(User).where(User.email == email))
            if existing:
                raise ValueError("邮箱已存在")

            user_count = session.scalar(select(func.count(User.id))) or 0
            role = "admin" if user_count == 0 else "member"
            user = User(
                id=uuid4().hex,
                name=name,
                email=email,
                password_hash=password_hash,
                role=role,
                status="active",
                quota_limit=None if role == "admin" else DEFAULT_REGISTER_MEMBER_QUOTA,
                quota_used=0,
            )
            session.add(user)
            session.flush()
            token = self._create_session(session, user)
            return {"token": token, "user": self._serialize_user(user)}

    def login(self, identifier: str, password: str) -> dict:
        identifier = str(identifier or "").strip()
        if not identifier:
            raise ValueError("请输入邮箱或用户名")
        with get_session() as session:
            if "@" in identifier:
                user = session.scalar(select(User).where(User.email == self._normalize_email(identifier)))
            else:
                user = session.scalar(select(User).where(User.name == identifier))
            if not user or not user.password_hash or not check_password_hash(user.password_hash, password or ""):
                raise ValueError("账号或密码不正确")
            if user.status != "active":
                raise ValueError("用户已停用")
            token = self._create_session(session, user)
            return {"token": token, "user": self._serialize_user(user)}

    def logout(self, token: str) -> None:
        token_hash = self._hash_token(token)
        with get_session() as session:
            session_obj = session.get(UserSession, token_hash)
            if session_obj:
                session.delete(session_obj)

    def current_user(self, token: str | None) -> dict | None:
        if not token:
            return None
        token_hash = self._hash_token(token)
        with get_session() as session:
            session_obj = session.get(UserSession, token_hash)
            if not session_obj or session_obj.expires_at <= datetime.now():
                if session_obj:
                    session.delete(session_obj)
                return None
            user = session_obj.user
            if not user or user.status != "active":
                return None
            return self._serialize_user(user)

    def _create_session(self, session, user: User) -> str:
        token = secrets.token_urlsafe(32)
        session.add(UserSession(
            token_hash=self._hash_token(token),
            user_id=user.id,
            expires_at=datetime.now() + timedelta(days=SESSION_DAYS),
        ))
        return token

    def _hash_token(self, token: str) -> str:
        return sha256(str(token or "").encode("utf-8")).hexdigest()

    def _normalize_name(self, name: str) -> str:
        value = str(name or "").strip()
        if not value:
            raise ValueError("用户名称不能为空")
        if len(value) > 80:
            raise ValueError("用户名称不能超过 80 个字符")
        return value

    def _normalize_email(self, email: str) -> str:
        value = str(email or "").strip().lower()
        if not EMAIL_PATTERN.match(value):
            raise ValueError("邮箱格式不正确")
        return value

    def _normalize_role(self, role: str) -> str:
        value = str(role or "member").strip()
        if value not in VALID_ROLES:
            raise ValueError("用户角色不正确")
        return value

    def _normalize_password(self, password: str) -> str:
        value = str(password or "")
        if len(value) < 6:
            raise ValueError("密码至少需要 6 位")
        if len(value) > 128:
            raise ValueError("密码不能超过 128 位")
        return value

    def _normalize_status(self, status: str) -> str:
        value = str(status or "active").strip()
        if value not in VALID_STATUSES:
            raise ValueError("用户状态不正确")
        return value

    def _normalize_quota_limit(self, value) -> int | None:
        if value in (None, ""):
            return None
        number = int(value)
        if number < 0:
            raise ValueError("生成额度不能小于 0")
        return number

    def _normalize_quota_used(self, value) -> int:
        number = int(value or 0)
        if number < 0:
            raise ValueError("已用额度不能小于 0")
        return number

    def _default_quota_limit_for_role(self, role: str) -> int | None:
        return None if role == "admin" else DEFAULT_REGISTER_MEMBER_QUOTA

    def _serialize_user(self, user: User) -> dict:
        quota_limit = user.quota_limit
        quota_used = user.quota_used or 0
        return {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "status": user.status,
            "quota_limit": quota_limit,
            "quota_used": quota_used,
            "quota_remaining": None if quota_limit is None else max(quota_limit - quota_used, 0),
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        }


_service_instance: UserService | None = None


def get_user_service() -> UserService:
    global _service_instance
    if _service_instance is None:
        _service_instance = UserService()
    return _service_instance
