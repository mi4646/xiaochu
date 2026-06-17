"""SQLite 会话存储后端。

设计要点：
- 单表 messages(session_id, idx, role, content, created_at)，复合主键保顺序
- 短连接：每次操作开关一次，避免长连接锁
- WAL 模式 + check_same_thread=False，兼容 FastAPI 多线程
- 不引入 ORM，3 条 SQL 解决
"""
import sqlite3
import time
from contextlib import contextmanager
from typing import Iterator

from core.config import get_settings
from core.logging import get_logger

logger = get_logger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    session_id TEXT NOT NULL,
    idx        INTEGER NOT NULL,
    role       TEXT NOT NULL,
    content    TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    PRIMARY KEY (session_id, idx)
);
"""


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    """短连接 + WAL，每次操作开关一次。"""
    path = get_settings().xiaochu_db_path
    conn = sqlite3.connect(path, check_same_thread=False, timeout=5.0)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """建表（幂等）。startup 调一次。"""
    with _connect() as conn:
        conn.executescript(_SCHEMA)
    logger.info("storage 初始化 path=%s", get_settings().xiaochu_db_path)


def append_message(session_id: str, role: str, content: str) -> None:
    """追加一条消息。idx 由当前最大值 + 1。"""
    with _connect() as conn:
        row = conn.execute(
            "SELECT COALESCE(MAX(idx), -1) FROM messages WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        next_idx = row[0] + 1
        conn.execute(
            "INSERT INTO messages(session_id, idx, role, content, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (session_id, next_idx, role, content, int(time.time())),
        )


def get_messages(session_id: str) -> list[dict]:
    """按 idx 升序返回 [{role, content}, ...]。未知 sid 返回 []。"""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE session_id = ? ORDER BY idx ASC",
            (session_id,),
        ).fetchall()
    return [{"role": r, "content": c} for r, c in rows]
