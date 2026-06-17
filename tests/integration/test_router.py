"""意图识别 classify_intent 测试。"""
from apps.chat.intents import Intent
from apps.chat.router import classify_intent


def test_classify_recipe(mock_chat):
    mock_chat.set_response("recipe")
    assert classify_intent("宫保鸡丁") == Intent.RECIPE


def test_classify_recommend(mock_chat):
    mock_chat.set_response("recommend")
    assert classify_intent("今晚吃什么") == Intent.RECOMMEND


def test_classify_ingredient(mock_chat):
    mock_chat.set_response("ingredient")
    assert classify_intent("冰箱里有鸡蛋") == Intent.INGREDIENT


def test_classify_cooking_qa(mock_chat):
    mock_chat.set_response("cooking_qa")
    assert classify_intent("怎么炒菜不糊") == Intent.COOKING_QA


def test_classify_chitchat(mock_chat):
    mock_chat.set_response("chitchat")
    assert classify_intent("你是谁") == Intent.CHITCHAT


def test_invalid_response_falls_back_to_chitchat(mock_chat):
    mock_chat.set_response("garbage_intent")
    assert classify_intent("xxx") == Intent.CHITCHAT


def test_empty_response_falls_back_to_chitchat(mock_chat):
    mock_chat.set_response("")
    assert classify_intent("xxx") == Intent.CHITCHAT


def test_strips_whitespace_and_picks_first_word(mock_chat):
    mock_chat.set_response("  recipe  \n some explanation")
    assert classify_intent("xxx") == Intent.RECIPE


def test_history_passed_to_llm(mock_chat):
    mock_chat.set_response("recipe")
    history = [{"role": "user", "content": "上轮"}, {"role": "assistant", "content": "回答"}]
    classify_intent("再来一道", history=history)
    # 历史前 4 条会被带上
    sent_messages = mock_chat.calls[0]["messages"]
    assert any(m.get("content") == "上轮" for m in sent_messages)
