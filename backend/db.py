import os
import shutil
from pathlib import Path
from contextlib import contextmanager

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DEFAULT_DATABASE_FILE = DATA_DIR / "shuguang-note.sqlite3"
LEGACY_DATABASE_FILE = DATA_DIR / "redink.sqlite3"


def _default_database_url() -> str:
    if LEGACY_DATABASE_FILE.exists() and not DEFAULT_DATABASE_FILE.exists():
        shutil.copy2(LEGACY_DATABASE_FILE, DEFAULT_DATABASE_FILE)
    return f"sqlite:///{DEFAULT_DATABASE_FILE}"


DATABASE_URL = (
    os.getenv("SHUGUANG_NOTE_DATABASE_URL")
    or os.getenv("REDINK_DATABASE_URL")
    or _default_database_url()
)

Base = declarative_base()


def _create_engine(database_url: str):
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, connect_args=connect_args, future=True)


engine = _create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def configure_database(database_url: str) -> None:
    """重新配置数据库连接，主要用于测试隔离。"""
    global DATABASE_URL, engine, SessionLocal

    engine.dispose()
    DATABASE_URL = database_url
    engine = _create_engine(DATABASE_URL)
    SessionLocal.configure(bind=engine)


def init_db() -> None:
    from backend import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_schema_columns()


def _ensure_schema_columns() -> None:
    """补齐轻量 schema 变更，避免无迁移框架时旧 SQLite 缺列。"""
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    with engine.begin() as connection:
        if "creations" in table_names:
            columns = {column["name"] for column in inspector.get_columns("creations")}
            if "user_id" not in columns:
                connection.execute(text("ALTER TABLE creations ADD COLUMN user_id VARCHAR(64)"))
        if "users" in table_names:
            columns = {column["name"] for column in inspector.get_columns("users")}
            if "password_hash" not in columns:
                connection.execute(text("ALTER TABLE users ADD COLUMN password_hash VARCHAR(255) NOT NULL DEFAULT ''"))
            if "quota_limit" not in columns:
                connection.execute(text("ALTER TABLE users ADD COLUMN quota_limit INTEGER"))
            if "quota_used" not in columns:
                connection.execute(text("ALTER TABLE users ADD COLUMN quota_used INTEGER NOT NULL DEFAULT 0"))
        for table_name in ("publish_accounts", "publish_drafts", "publish_jobs"):
            if table_name in table_names:
                columns = {column["name"] for column in inspector.get_columns(table_name)}
                if "user_id" not in columns:
                    connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN user_id VARCHAR(64)"))


@contextmanager
def get_session():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
