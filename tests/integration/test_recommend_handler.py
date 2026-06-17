"""recommend handler 数量识别 / 上限 / 失败容错测试。"""
import json

from apps.recommend.handler import handle


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


def test_default_count_when_user_does_not_specify(mock_chat):
    # 推荐 5 道、用户没明说数量 → desired_count=3
    rec = json.dumps({"dishes": list("ABCDE"), "desired_count": 3})
    recipes = [json.dumps([_fake_recipe(n)]) for n in "ABC"]
    mock_chat.set_responses([rec] + recipes)

    out = handle("今晚吃什么")
    assert out["dishes"] == list("ABCDE")
    assert len(out["recipes"]) == 3


def test_user_specifies_count_within_max(mock_chat):
    rec = json.dumps({"dishes": list("ABCDE"), "desired_count": 5})
    recipes = [json.dumps([_fake_recipe(n)]) for n in "ABCDE"]
    mock_chat.set_responses([rec] + recipes)

    out = handle("推荐 5 道")
    assert len(out["recipes"]) == 5


def test_user_count_exceeds_max_truncated(mock_chat):
    # 用户要 10 道，desired_count=10，应被截到 7
    rec = json.dumps({"dishes": list("ABCDEFGHIJ"), "desired_count": 10})
    recipes = [json.dumps([_fake_recipe(n)]) for n in "ABCDEFG"]
    mock_chat.set_responses([rec] + recipes)

    out = handle("推荐 10 道")
    assert len(out["recipes"]) == 7
    assert "分批" in out["note"]


def test_dishes_count_smaller_than_desired(mock_chat):
    # LLM 只推荐了 2 道，但 desired_count=3 → 不应越界
    rec = json.dumps({"dishes": ["A", "B"], "desired_count": 3})
    recipes = [json.dumps([_fake_recipe(n)]) for n in "AB"]
    mock_chat.set_responses([rec] + recipes)

    out = handle("xxx")
    assert len(out["recipes"]) == 2


def test_one_recipe_failure_does_not_block_others(mock_chat):
    rec = json.dumps({"dishes": ["A", "B"], "desired_count": 2})
    # A 成功、B 解析失败
    mock_chat.set_responses([rec, json.dumps([_fake_recipe("A")]), "this is broken"])

    out = handle("xxx")
    assert len(out["recipes"]) == 2
    # 必须有一个成功一个 error
    has_ok = any("dish_name" in r for r in out["recipes"])
    has_err = any("error" in r for r in out["recipes"])
    assert has_ok and has_err
