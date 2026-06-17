"""POST /chat 端到端测试。"""
import json

from fastapi.testclient import TestClient

from main import app


def _fake_recipe(name: str) -> dict:
    return {
        "dish_name": name,
        "ingredients": [{"name": "盐", "amount": "5g"}],
        "steps": [{"order": 1, "description": "翻炒"}],
        "tips": ["少放盐"],
        "nutrition": {
            "calories": "300 kcal",
            "difficulty": "简单",
            "cook_time": "10 分钟",
            "servings": "1 人份",
        },
    }


def test_root_endpoint():
    client = TestClient(app)
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["app"] == "xiaochu"


def test_chat_recipe_flow(mock_chat):
    # 第一次：意图识别返回 "recipe"
    # 第二次：handler 返回菜谱 JSON
    mock_chat.set_responses([
        "recipe",
        json.dumps([_fake_recipe("番茄炒蛋")]),
    ])

    client = TestClient(app)
    r = client.post("/chat", json={"message": "番茄炒蛋"})
    assert r.status_code == 200
    body = r.json()
    assert body["intent"] == "recipe"
    assert body["data"]["recipes"][0]["dish_name"] == "番茄炒蛋"
    assert body["session_id"]


def test_chat_session_id_reused(mock_chat):
    """同一 session_id 能继续对话，且 history 累积。"""
    mock_chat.set_responses([
        "cooking_qa", "锅要预热。",          # 第 1 轮
        "cooking_qa", "油温到 7 成。",         # 第 2 轮
    ])

    client = TestClient(app)
    r1 = client.post("/chat", json={"message": "怎么炒菜不糊"})
    sid = r1.json()["session_id"]
    assert r1.json()["data"]["answer"] == "锅要预热。"

    r2 = client.post("/chat", json={"message": "再说说", "session_id": sid})
    assert r2.json()["session_id"] == sid
    assert r2.json()["data"]["answer"] == "油温到 7 成。"

    # 第二轮的意图识别应该看到第一轮的 history
    second_intent_call = mock_chat.calls[2]  # call 0/1=第一轮，2=第二轮意图识别
    sent = second_intent_call["messages"]
    assert any(m.get("content") == "怎么炒菜不糊" for m in sent)


def test_chat_unknown_session_id_is_respected(mock_chat):
    """客户端传未知 sid 时，服务端应采纳而非偷换。"""
    mock_chat.set_responses(["chitchat", "你好"])
    client = TestClient(app)
    sid = "708100861ce74915aa2514af984e572b"
    r = client.post("/chat", json={"message": "嗨", "session_id": sid})
    assert r.status_code == 200
    assert r.json()["session_id"] == sid


def test_chat_empty_message_rejected():
    client = TestClient(app)
    r = client.post("/chat", json={"message": ""})
    assert r.status_code == 422  # Pydantic validation


def test_chat_handler_error_returns_500(mock_chat):
    # 意图识别成功，但 handler 解析时崩溃
    mock_chat.set_responses(["recipe", "this is not json"])
    client = TestClient(app)
    r = client.post("/chat", json={"message": "随便"})
    assert r.status_code == 500
    assert "处理失败" in r.json()["detail"]
