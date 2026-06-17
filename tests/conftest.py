"""共享 fixture：mock LLM、清会话、注入测试 env。"""
import os
import sys
from pathlib import Path

import pytest

# 把项目根目录加入 sys.path，让 tests 里的 import 能找到 apps/core
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# 测试期默认 env，避免 Settings 校验报错
os.environ.setdefault("OPENAI_API_KEY", "sk-test")
os.environ.setdefault("OPENAI_BASE_URL", "https://api.test/v1")
os.environ.setdefault("XIAOCHU_MODEL", "test-model")
# 日志：测试不输出到控制台、写到临时目录，避免污染仓库
import tempfile as _tempfile
os.environ.setdefault("XIAOCHU_LOG_TO_CONSOLE", "0")
os.environ.setdefault("XIAOCHU_LOG_DIR", _tempfile.mkdtemp(prefix="xiaochu-test-logs-"))
os.environ.setdefault("XIAOCHU_LOG_LEVEL", "WARNING")


class FakeChat:
    """可控的 chat 替身：按顺序返回预设响应，记录调用。"""

    def __init__(self) -> None:
        self.responses: list[str] = []
        self.calls: list[dict] = []

    def set_response(self, text: str) -> None:
        self.responses = [text]

    def set_responses(self, texts: list[str]) -> None:
        self.responses = list(texts)

    def __call__(self, messages, **kwargs):
        self.calls.append({"messages": messages, "kwargs": kwargs})
        if not self.responses:
            return ""
        return self.responses.pop(0)


@pytest.fixture
def mock_chat(monkeypatch):
    """替换所有 handler / router / dispatcher 模块里的 chat 函数。"""
    import apps.chat.dispatcher
    import apps.chat.router
    import apps.ingredient.handler
    import apps.qa.handler
    import apps.recipe.handler
    import apps.recommend.handler

    fake = FakeChat()
    targets = [
        apps.chat.router,
        apps.chat.dispatcher,
        apps.recipe.handler,
        apps.recommend.handler,
        apps.ingredient.handler,
        apps.qa.handler,
    ]
    for mod in targets:
        monkeypatch.setattr(mod, "chat", fake)
    return fake


@pytest.fixture(autouse=True)
def _clean_session_store(tmp_path, monkeypatch):
    """每个测试用例独立的 SQLite 文件，避免互相污染。"""
    from apps.chat import session
    from core import storage
    from core.config import get_settings

    db_file = tmp_path / "xiaochu-test.db"
    settings = get_settings()
    monkeypatch.setattr(settings, "xiaochu_db_path", str(db_file))
    storage.init_db()

    original = session._store
    session._store = session.SessionStore()
    yield
    session._store = original
