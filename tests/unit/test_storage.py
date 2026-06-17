"""core/storage 单元测试。临时 db 由 conftest 的 _clean_session_store 提供。"""
from core import storage


def test_init_db_is_idempotent():
    """重复 init 不应报错。"""
    storage.init_db()
    storage.init_db()  # 第二次也应成功
    assert storage.get_messages("any") == []


def test_append_then_get_preserves_order():
    sid = "sess-a"
    storage.append_message(sid, "user", "你好")
    storage.append_message(sid, "assistant", "陛下好")
    storage.append_message(sid, "user", "再见")
    assert storage.get_messages(sid) == [
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "陛下好"},
        {"role": "user", "content": "再见"},
    ]


def test_sessions_are_isolated():
    """不同 sid 互不影响。"""
    storage.append_message("sess-a", "user", "A 的消息")
    storage.append_message("sess-b", "user", "B 的消息")
    assert storage.get_messages("sess-a") == [{"role": "user", "content": "A 的消息"}]
    assert storage.get_messages("sess-b") == [{"role": "user", "content": "B 的消息"}]


def test_get_unknown_session_returns_empty_list():
    assert storage.get_messages("never-touched") == []


def test_special_chars_preserved():
    """SQL 参数化 + 中文/引号/换行不被破坏。"""
    sid = "sess-x"
    content = "包含 ' 引号、\"双引号、\n 换行 和 中文"
    storage.append_message(sid, "user", content)
    assert storage.get_messages(sid) == [{"role": "user", "content": content}]
