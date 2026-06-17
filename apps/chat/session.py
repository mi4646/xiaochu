"""会话状态管理：内存 dict 起步，重启丢失。"""
import uuid
from threading import Lock


class SessionStore:
    """简单的线程安全内存会话存储。"""

    def __init__(self) -> None:
        self._data: dict[str, list[dict]] = {}
        self._lock = Lock()

    def create(self) -> str:
        sid = uuid.uuid4().hex
        with self._lock:
            self._data[sid] = []
        return sid

    def ensure(self, session_id: str | None) -> str:
        """有则用，无则建。"""
        if session_id and session_id in self._data:
            return session_id
        return self.create()

    def get(self, session_id: str) -> list[dict]:
        """返回历史消息列表副本。"""
        with self._lock:
            return list(self._data.get(session_id, []))

    def append(self, session_id: str, role: str, content: str) -> None:
        with self._lock:
            self._data.setdefault(session_id, []).append({"role": role, "content": content})


_store = SessionStore()


def get_store() -> SessionStore:
    return _store
