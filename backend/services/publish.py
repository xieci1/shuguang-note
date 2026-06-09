"""发布中心服务。

首版只实现小红书发布底座：账号、草稿、任务与 CLI 执行器适配。
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from sqlalchemy import select

from backend.db import get_session, init_db
from backend.models import Creation, PublishAccount, PublishDraft, PublishJob
from backend.services.history import get_history_service


class PublishStatus:
    DRAFT = "draft"
    QUEUED = "queued"
    RUNNING = "running"
    READY_FOR_REVIEW = "ready_for_review"
    FAILED = "failed"
    CANCELLED = "cancelled"


SUPPORTED_PLATFORMS = {"xhs"}


class PublisherAdapter:
    platform = "xhs"

    def __init__(self, config: Dict[str, Any], root_dir: Path):
        self.config = config
        self.root_dir = root_dir

    def validate_account(self, account: PublishAccount) -> None:
        if account.platform != self.platform:
            raise ValueError(f"账号平台不匹配: {account.platform}")
        self._resolve_path(account.profile_dir).mkdir(parents=True, exist_ok=True)

    def prepare_payload(self, account: PublishAccount, draft: PublishDraft) -> Dict[str, Any]:
        media = _loads_json(draft.media_json, [])
        tags = _loads_json(draft.tags_json, [])
        return {
            "platform": self.platform,
            "account": {
                "id": account.id,
                "name": account.name,
                "profile_dir": str(self._resolve_path(account.profile_dir)),
            },
            "post": {
                "title": draft.title,
                "body": draft.body,
                "tags": tags,
                "media": media,
                "click_publish": True,
            },
        }

    def open_login(self, account: PublishAccount) -> Dict[str, Any]:
        command = self.config.get("login_command") or self.config.get("command")
        if not command:
            return {
                "success": False,
                "error": "未配置小红书登录执行器。请在 publish_providers.yaml 配置 login_command 或 command。",
            }
        payload = {
            "action": "login",
            "platform": self.platform,
            "account": {
                "id": account.id,
                "name": account.name,
                "profile_dir": str(self._resolve_path(account.profile_dir)),
            },
        }
        return self._run_command(command, payload, wait=False)

    def publish_draft(self, account: PublishAccount, draft: PublishDraft) -> Dict[str, Any]:
        command = self.config.get("command")
        if not command:
            return {
                "success": False,
                "error": "未配置小红书发布执行器。请在 publish_providers.yaml 配置 xhs.command。",
            }
        payload = self.prepare_payload(account, draft)
        return self._run_command(command, payload, wait=True)

    def _run_command(self, command, payload: Dict[str, Any], wait: bool) -> Dict[str, Any]:
        timeout = int(self.config.get("timeout_seconds", 900))
        workdir = str(self._resolve_path(self.config.get("working_dir") or "."))
        env = os.environ.copy()
        extra_env = self.config.get("env") or {}
        if isinstance(extra_env, dict):
            env.update({str(key): str(value) for key, value in extra_env.items()})
        if not wait:
            temp_file = tempfile.NamedTemporaryFile(
                prefix="shuguang_note_publish_",
                suffix=".json",
                delete=False,
                mode="w",
                encoding="utf-8",
            )
            with temp_file:
                json.dump(payload, temp_file, ensure_ascii=False, indent=2)
            args = _command_args(command) + [temp_file.name]
            subprocess.Popen(args, cwd=workdir, env=env)
            return {"success": True, "logs": "登录窗口已打开"}

        with tempfile.TemporaryDirectory(prefix="shuguang_note_publish_") as temp_dir:
            payload_path = Path(temp_dir) / "payload.json"
            payload_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            args = _command_args(command) + [str(payload_path)]
            completed = subprocess.run(
                args,
                cwd=workdir,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
            )
            stdout = completed.stdout or ""
            stderr = completed.stderr or ""
            logs = "\n".join(part for part in [stdout.strip(), stderr.strip()] if part)
            parsed = _parse_command_output(stdout)
            if completed.returncode != 0:
                return {
                    "success": False,
                    "error": parsed.get("error") or logs or f"发布执行器退出码 {completed.returncode}",
                    "logs": logs,
                }
            return {
                "success": bool(parsed.get("success", True)),
                "error": parsed.get("error"),
                "logs": logs or json.dumps(parsed, ensure_ascii=False),
            }

    def _resolve_path(self, value: str) -> Path:
        path = Path(str(value)).expanduser()
        if not path.is_absolute():
            path = self.root_dir / path
        return path.resolve()


class PublishService:
    def __init__(self):
        self.root_dir = Path(__file__).resolve().parent.parent.parent
        self.profile_root = self.root_dir / "data" / "browser_profiles"
        self.config_path = self.root_dir / "publish_providers.yaml"
        self._active_accounts: set[str] = set()
        self._active_logins: set[str] = set()
        self._lock = threading.Lock()
        init_db()

    def list_accounts(self, platform: Optional[str] = None, current_user: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        with get_session() as session:
            stmt = select(PublishAccount).order_by(PublishAccount.created_at.desc())
            if platform:
                stmt = stmt.where(PublishAccount.platform == platform)
            if current_user and current_user.get("role") != "admin":
                stmt = stmt.where(PublishAccount.user_id == current_user.get("id"))
            return [self._serialize_account(account) for account in session.scalars(stmt).all()]

    def list_jobs(self, limit: int = 50, current_user: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        with get_session() as session:
            stmt = select(PublishJob).order_by(PublishJob.created_at.desc()).limit(max(1, min(limit, 200)))
            if current_user and current_user.get("role") != "admin":
                stmt = stmt.where(PublishJob.user_id == current_user.get("id"))
            return [self._serialize_job(job) for job in session.scalars(stmt).all()]

    def create_account(self, name: str, platform: str = "xhs", current_user: Optional[Dict[str, Any]] = None) -> str:
        platform = platform or "xhs"
        if platform not in SUPPORTED_PLATFORMS:
            raise ValueError(f"暂不支持发布平台: {platform}")
        if not name:
            raise ValueError("账号名称不能为空")
        user_id = current_user.get("id") if current_user else None
        with get_session() as session:
            existing = session.scalar(
                select(PublishAccount).where(
                    PublishAccount.platform == platform,
                    PublishAccount.name == name,
                    PublishAccount.user_id == user_id,
                )
            )
            if existing:
                raise ValueError("同名发布账号已存在")
        account_id = str(uuid.uuid4())
        profile_dir = Path("data") / "browser_profiles" / platform / account_id
        (self.root_dir / profile_dir).mkdir(parents=True, exist_ok=True)
        now = datetime.now()
        with get_session() as session:
            account = PublishAccount(
                id=account_id,
                user_id=user_id,
                platform=platform,
                name=name,
                profile_dir=profile_dir.as_posix(),
                status="created",
                created_at=now,
                updated_at=now,
            )
            session.add(account)
        return account_id

    def delete_account(self, account_id: str, current_user: Optional[Dict[str, Any]] = None) -> bool:
        with get_session() as session:
            account = session.get(PublishAccount, account_id)
            if not account:
                return False
            if not self._can_access(account.user_id, current_user):
                return False
            session.delete(account)
        return True

    def open_login(self, account_id: str, current_user: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        with get_session() as session:
            account = session.get(PublishAccount, account_id)
            if not account:
                return {"success": False, "error": "发布账号不存在"}
            if not self._can_access(account.user_id, current_user):
                return {"success": False, "error": "无权操作该发布账号"}
            adapter = self._get_adapter(account.platform)
            adapter.validate_account(account)
            with self._lock:
                if account.id in self._active_logins:
                    return {"success": True, "logs": "登录窗口已打开，请在浏览器中完成登录"}
                self._active_logins.add(account.id)
            result = adapter.open_login(account)
            if result.get("success"):
                account.status = "login_opened"
                account.last_login_at = datetime.now()
                account.updated_at = datetime.now()
                timer = threading.Timer(300, self._release_login_lock, args=(account.id,))
                timer.daemon = True
                timer.start()
            else:
                self._release_login_lock(account.id)
            return result

    def create_draft(
        self,
        creation_id: str,
        account_id: str,
        title: str,
        body: str,
        tags: List[str],
        page_indexes: Optional[List[int]] = None,
        current_user: Optional[Dict[str, Any]] = None,
    ) -> str:
        if not title:
            raise ValueError("发布标题不能为空")
        if not body:
            raise ValueError("发布正文不能为空")
        with get_session() as session:
            account = session.get(PublishAccount, account_id)
            if not account:
                raise ValueError("发布账号不存在")
            if not self._can_access(account.user_id, current_user):
                raise ValueError("无权使用该发布账号")
            creation = session.get(Creation, creation_id)
            if not creation:
                raise ValueError("创作记录不存在")
            if not self._can_access(creation.user_id, current_user):
                raise ValueError("无权发布该作品")
            selected_page_indexes = self._normalize_page_indexes(page_indexes)
            media = self._media_for_creation(creation, selected_page_indexes)
            if not media:
                raise ValueError("没有可发布的已生成图片")
            now = datetime.now()
            draft_id = str(uuid.uuid4())
            draft = PublishDraft(
                id=draft_id,
                user_id=current_user.get("id") if current_user else creation.user_id,
                creation_id=creation_id,
                account_id=account_id,
                platform=account.platform,
                title=title,
                body=body,
                tags_json=json.dumps(tags or [], ensure_ascii=False),
                media_json=json.dumps(media, ensure_ascii=False),
                status=PublishStatus.DRAFT,
                created_at=now,
                updated_at=now,
            )
            session.add(draft)
        return draft_id

    def run_draft(self, draft_id: str, current_user: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        with get_session() as session:
            draft = session.get(PublishDraft, draft_id)
            if not draft:
                return {"success": False, "error": "发布草稿不存在"}
            if not self._can_access(draft.user_id, current_user):
                return {"success": False, "error": "无权操作该发布草稿"}
            account = session.get(PublishAccount, draft.account_id) if draft.account_id else None
            if not account:
                return {"success": False, "error": "发布账号不存在"}
            if not self._can_access(account.user_id, current_user):
                return {"success": False, "error": "无权使用该发布账号"}
            with self._lock:
                if account.id in self._active_accounts:
                    return {"success": False, "error": "该账号已有发布任务运行中，请稍后再试"}
                self._active_accounts.add(account.id)
            now = datetime.now()
            job = PublishJob(
                id=str(uuid.uuid4()),
                user_id=draft.user_id,
                draft_id=draft.id,
                account_id=account.id,
                platform=draft.platform,
                status=PublishStatus.QUEUED,
                created_at=now,
                updated_at=now,
            )
            draft.status = PublishStatus.QUEUED
            draft.updated_at = now
            session.add(job)
            job_id = job.id

        thread = threading.Thread(target=self._run_job, args=(job_id,), daemon=True)
        thread.start()
        return {"success": True, "job_id": job_id}

    def get_job(self, job_id: str, current_user: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        with get_session() as session:
            job = session.get(PublishJob, job_id)
            if not job:
                return None
            if not self._can_access(job.user_id, current_user):
                return None
            return self._serialize_job(job)

    def cancel_job(self, job_id: str, current_user: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        with get_session() as session:
            job = session.get(PublishJob, job_id)
            if not job:
                return {"success": False, "error": "发布任务不存在"}
            if not self._can_access(job.user_id, current_user):
                return {"success": False, "error": "无权操作该发布任务"}
            if job.status == PublishStatus.RUNNING:
                return {"success": False, "error": "任务已开始执行，首版暂不支持中断外部发布器"}
            job.status = PublishStatus.CANCELLED
            job.finished_at = datetime.now()
            job.updated_at = datetime.now()
            if job.draft:
                job.draft.status = PublishStatus.CANCELLED
        return {"success": True}

    def _run_job(self, job_id: str) -> None:
        account_id = None
        try:
            with get_session() as session:
                job = session.get(PublishJob, job_id)
                if not job:
                    return
                draft = job.draft
                account = job.account
                if not draft or not account:
                    job.status = PublishStatus.FAILED
                    job.error = "发布草稿或账号不存在"
                    job.finished_at = datetime.now()
                    return
                account_id = account.id
                job.status = PublishStatus.RUNNING
                job.started_at = datetime.now()
                job.updated_at = datetime.now()
                draft.status = PublishStatus.RUNNING

            with get_session() as session:
                job = session.get(PublishJob, job_id)
                draft = job.draft
                account = job.account
                adapter = self._get_adapter(job.platform)
                adapter.validate_account(account)
                result = adapter.publish_draft(account, draft)
                now = datetime.now()
                if result.get("success"):
                    job.status = PublishStatus.READY_FOR_REVIEW
                    job.error = None
                    draft.status = PublishStatus.READY_FOR_REVIEW
                    draft.error = None
                else:
                    job.status = PublishStatus.FAILED
                    job.error = result.get("error") or "发布执行器失败"
                    draft.status = PublishStatus.FAILED
                    draft.error = job.error
                job.logs = result.get("logs") or ""
                job.finished_at = now
                job.updated_at = now
                draft.updated_at = now
        except Exception as exc:
            with get_session() as session:
                job = session.get(PublishJob, job_id)
                if job:
                    job.status = PublishStatus.FAILED
                    job.error = str(exc)
                    job.logs = (job.logs or "") + f"\n{exc}"
                    job.finished_at = datetime.now()
                    job.updated_at = datetime.now()
                    if job.draft:
                        job.draft.status = PublishStatus.FAILED
                        job.draft.error = str(exc)
        finally:
            if account_id:
                with self._lock:
                    self._active_accounts.discard(account_id)

    def _release_login_lock(self, account_id: str) -> None:
        with self._lock:
            self._active_logins.discard(account_id)

    def _media_for_creation(self, creation: Creation, page_indexes: Optional[List[int]] = None) -> List[Dict[str, Any]]:
        if not creation.task_id:
            return []
        history_dir = Path(get_history_service().history_dir)
        task_dir = history_dir / creation.task_id
        media = []
        seen_paths = set()
        allowed_indexes = set(page_indexes) if page_indexes is not None else None
        for image in sorted(creation.images, key=lambda item: item.page_index):
            if allowed_indexes is not None and image.page_index not in allowed_indexes:
                continue
            if image.status != "done" or not image.filename:
                continue
            image_path = task_dir / image.filename
            resolved_path = str(image_path.resolve())
            if image_path.exists() and resolved_path not in seen_paths:
                seen_paths.add(resolved_path)
                media.append({
                    "page_index": image.page_index,
                    "filename": image.filename,
                    "path": resolved_path,
                })
        return media

    def _normalize_page_indexes(self, value: Any) -> Optional[List[int]]:
        if value in (None, ""):
            return None
        if not isinstance(value, list):
            raise ValueError("发布页码格式不正确")
        indexes = []
        for item in value:
            try:
                index = int(item)
            except (TypeError, ValueError):
                raise ValueError("发布页码必须是数字")
            if index < 0:
                raise ValueError("发布页码不能小于 0")
            if index not in indexes:
                indexes.append(index)
        return indexes

    def _get_adapter(self, platform: str) -> PublisherAdapter:
        if platform != "xhs":
            raise ValueError(f"暂不支持发布平台: {platform}")
        config = self._load_config().get("platforms", {}).get(platform, {})
        if not config:
            raise ValueError("未配置小红书发布器，请复制 publish_providers.yaml.example 并填写执行器命令")
        if config.get("enabled") is False:
            raise ValueError("小红书发布器未启用")
        return PublisherAdapter(config, self.root_dir)

    def _load_config(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            return {"platforms": {}}
        with open(self.config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _serialize_account(self, account: PublishAccount) -> Dict[str, Any]:
        return {
            "id": account.id,
            "user_id": account.user_id,
            "user": self._serialize_user(account.user),
            "platform": account.platform,
            "name": account.name,
            "profile_dir": account.profile_dir,
            "status": account.status,
            "last_login_at": account.last_login_at.isoformat() if account.last_login_at else None,
            "created_at": account.created_at.isoformat(),
            "updated_at": account.updated_at.isoformat(),
        }

    def _serialize_job(self, job: PublishJob) -> Dict[str, Any]:
        return {
            "id": job.id,
            "user_id": job.user_id,
            "user": self._serialize_user(job.user),
            "draft_id": job.draft_id,
            "account_id": job.account_id,
            "account_name": job.account.name if job.account else None,
            "draft_title": job.draft.title if job.draft else None,
            "creation_id": job.draft.creation_id if job.draft else None,
            "platform": job.platform,
            "status": job.status,
            "logs": job.logs,
            "error": job.error,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "finished_at": job.finished_at.isoformat() if job.finished_at else None,
            "created_at": job.created_at.isoformat(),
            "updated_at": job.updated_at.isoformat(),
        }

    def _can_access(self, owner_id: Optional[str], current_user: Optional[Dict[str, Any]]) -> bool:
        if not current_user:
            return True
        if current_user.get("role") == "admin":
            return True
        return bool(owner_id and owner_id == current_user.get("id"))

    def _serialize_user(self, user) -> Optional[Dict[str, Any]]:
        if not user:
            return None
        return {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
        }


def _loads_json(value: str, fallback):
    try:
        return json.loads(value)
    except Exception:
        return fallback


def _parse_command_output(stdout: str) -> Dict[str, Any]:
    text = (stdout or "").strip()
    if not text:
        return {}
    for line in reversed(text.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            return json.loads(line)
        except Exception:
            continue
    return {}


def _command_args(command) -> List[str]:
    if isinstance(command, list):
        return [str(item) for item in command]
    if isinstance(command, str):
        import shlex
        return shlex.split(command)
    raise ValueError("发布执行器 command 必须是字符串或数组")


_service_instance = None


def get_publish_service() -> PublishService:
    global _service_instance
    if _service_instance is None:
        _service_instance = PublishService()
    return _service_instance
