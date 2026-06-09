from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="member", index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True)
    quota_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quota_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    sessions: Mapped[list["UserSession"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class UserSession(Base):
    __tablename__ = "user_sessions"

    token_hash: Mapped[str] = mapped_column(String(128), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)

    user: Mapped[User] = relationship(back_populates="sessions")


class Creation(Base):
    __tablename__ = "creations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft", index=True)
    thumbnail: Mapped[str | None] = mapped_column(String(255), nullable=True)
    task_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    outline_raw: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    pages: Mapped[list["OutlinePage"]] = relationship(
        back_populates="creation",
        cascade="all, delete-orphan",
        order_by="OutlinePage.page_index",
    )
    images: Mapped[list["GeneratedImage"]] = relationship(
        back_populates="creation",
        cascade="all, delete-orphan",
        order_by="GeneratedImage.page_index",
    )
    content: Mapped["GeneratedContent | None"] = relationship(
        back_populates="creation",
        cascade="all, delete-orphan",
        uselist=False,
    )
    tasks: Mapped[list["ImageTask"]] = relationship(
        back_populates="creation",
        cascade="all, delete-orphan",
    )
    publish_drafts: Mapped[list["PublishDraft"]] = relationship(
        back_populates="creation",
        cascade="all, delete-orphan",
    )
    user: Mapped["User | None"] = relationship()


class OutlinePage(Base):
    __tablename__ = "outline_pages"
    __table_args__ = (UniqueConstraint("creation_id", "page_index", name="uq_outline_page"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    creation_id: Mapped[str] = mapped_column(ForeignKey("creations.id", ondelete="CASCADE"), index=True)
    page_index: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[str] = mapped_column(String(32), nullable=False, default="content")
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")

    creation: Mapped[Creation] = relationship(back_populates="pages")


class GeneratedImage(Base):
    __tablename__ = "generated_images"
    __table_args__ = (UniqueConstraint("task_id", "page_index", name="uq_task_page_image"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    creation_id: Mapped[str] = mapped_column(ForeignKey("creations.id", ondelete="CASCADE"), index=True)
    task_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    page_index: Mapped[int] = mapped_column(Integer, nullable=False)
    filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="generating")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    creation: Mapped[Creation] = relationship(back_populates="images")


class GeneratedContent(Base):
    __tablename__ = "generated_contents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    creation_id: Mapped[str] = mapped_column(ForeignKey("creations.id", ondelete="CASCADE"), unique=True, index=True)
    titles_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    copywriting: Mapped[str] = mapped_column(Text, nullable=False, default="")
    tags_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    creation: Mapped[Creation] = relationship(back_populates="content")


class ImageTask(Base):
    __tablename__ = "image_tasks"

    task_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    creation_id: Mapped[str | None] = mapped_column(ForeignKey("creations.id", ondelete="SET NULL"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="generating")
    total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    creation: Mapped[Creation | None] = relationship(back_populates="tasks")


class PublishAccount(Base):
    __tablename__ = "publish_accounts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    platform: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    profile_dir: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="created", index=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    drafts: Mapped[list["PublishDraft"]] = relationship(back_populates="account")
    jobs: Mapped[list["PublishJob"]] = relationship(back_populates="account")
    user: Mapped["User | None"] = relationship()


class PublishDraft(Base):
    __tablename__ = "publish_drafts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    creation_id: Mapped[str] = mapped_column(ForeignKey("creations.id", ondelete="CASCADE"), index=True)
    account_id: Mapped[str | None] = mapped_column(ForeignKey("publish_accounts.id", ondelete="SET NULL"), nullable=True, index=True)
    platform: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    tags_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    media_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft", index=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    creation: Mapped[Creation] = relationship(back_populates="publish_drafts")
    account: Mapped[PublishAccount | None] = relationship(back_populates="drafts")
    user: Mapped["User | None"] = relationship()
    jobs: Mapped[list["PublishJob"]] = relationship(
        back_populates="draft",
        cascade="all, delete-orphan",
    )


class PublishJob(Base):
    __tablename__ = "publish_jobs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    draft_id: Mapped[str] = mapped_column(ForeignKey("publish_drafts.id", ondelete="CASCADE"), index=True)
    account_id: Mapped[str | None] = mapped_column(ForeignKey("publish_accounts.id", ondelete="SET NULL"), nullable=True, index=True)
    platform: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued", index=True)
    logs: Mapped[str] = mapped_column(Text, nullable=False, default="")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    draft: Mapped[PublishDraft] = relationship(back_populates="jobs")
    account: Mapped[PublishAccount | None] = relationship(back_populates="jobs")
    user: Mapped["User | None"] = relationship()
