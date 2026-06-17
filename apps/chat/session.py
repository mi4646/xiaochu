"""会话状态管理：SQLite 后端，存储字段见 core/storage.py。

对外 API 与早期内存版保持一致（create/ensure/get/append），
所以 routes/cli/handler 层零感知。
"""
import uuid

from core import storage


class SessionStore:
    """SQLite 支撑的会话存储。SessionStore 本身无状态，方法直接转 storage。"""

    def create(self) -> str:
        """生成新 sid。不立即落库，等首次 append 时再插，避免空会话堆积。"""
        return uuid.uuid4().hex

    def ensure(self, session_id: str | None) -> str:
        """有 sid 则采纳（不强制 DB 里已存在），无 sid 才新建。"""
        if session_id:
            return session_id
        return self.create()

    def get(self, session_id: str) -> list[dict]:
        """返回历史消息列表。未知 sid 返回空 list。"""
        return storage.get_messages(session_id)

    def append(self, session_id: str, role: str, content: str) -> None:
        storage.append_message(session_id, role, content)


_store = SessionStore()


def get_store() -> SessionStore:
    return _store
