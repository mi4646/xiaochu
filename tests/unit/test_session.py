"""SessionStore 单元测试。"""
from apps.chat.session import SessionStore


def test_create_returns_unique_ids():
    s = SessionStore()
    a, b = s.create(), s.create()
    assert a != b
    assert len(a) == 32  # uuid4 hex


def test_ensure_creates_when_unknown():
    s = SessionStore()
    sid = s.ensure(None)
    assert sid in s._data


def test_ensure_creates_when_id_not_in_store():
    s = SessionStore()
    sid = s.ensure("nonexistent")
    assert sid != "nonexistent"
    assert sid in s._data


def test_ensure_keeps_existing_id():
    s = SessionStore()
    sid = s.create()
    assert s.ensure(sid) == sid


def test_append_and_get():
    s = SessionStore()
    sid = s.create()
    s.append(sid, "user", "hi")
    s.append(sid, "assistant", "hello")
    history = s.get(sid)
    assert history == [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    ]


def test_get_returns_copy_not_reference():
    s = SessionStore()
    sid = s.create()
    s.append(sid, "user", "a")
    h = s.get(sid)
    h.append({"role": "user", "content": "tampered"})
    assert len(s.get(sid)) == 1


def test_get_unknown_returns_empty():
    s = SessionStore()
    assert s.get("nonexistent") == []
