"""dispatch 五分支集成测试。"""
import json

from apps.chat.dispatcher import dispatch
from apps.chat.intents import Intent


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


def test_dispatch_recipe(mock_chat):
    mock_chat.set_response(json.dumps([_fake_recipe("番茄炒蛋")]))
    out = dispatch(Intent.RECIPE, "番茄炒蛋", history=[])
    assert "recipes" in out
    assert out["recipes"][0]["dish_name"] == "番茄炒蛋"


def test_dispatch_recipe_multi_dishes(mock_chat):
    mock_chat.set_response(
        json.dumps([_fake_recipe("宫保鸡丁"), _fake_recipe("木须肉")])
    )
    out = dispatch(Intent.RECIPE, "宫保鸡丁+木须肉", history=[])
    assert len(out["recipes"]) == 2


def test_dispatch_recommend(mock_chat):
    # 1 次 LLM：返回推荐 JSON（dishes + desired_count）
    # 然后并发对每道菜调 recipe handler 的 LLM
    recommend_resp = json.dumps({"dishes": ["A", "B"], "desired_count": 2})
    recipe_a = json.dumps([_fake_recipe("A")])
    recipe_b = json.dumps([_fake_recipe("B")])
    mock_chat.set_responses([recommend_resp, recipe_a, recipe_b])

    out = dispatch(Intent.RECOMMEND, "推荐两道菜", history=[])
    assert out["dishes"] == ["A", "B"]
    assert len(out["recipes"]) == 2
    assert {r["dish_name"] for r in out["recipes"]} == {"A", "B"}


def test_dispatch_ingredient(mock_chat):
    mock_chat.set_response("番茄炒蛋\n蒸蛋羹\n紫菜蛋花汤")
    out = dispatch(Intent.INGREDIENT, "冰箱里有鸡蛋", history=[])
    assert "番茄炒蛋" in out["dishes"]
    assert len(out["dishes"]) == 3


def test_dispatch_cooking_qa(mock_chat):
    mock_chat.set_response("锅要预热充分。")
    out = dispatch(Intent.COOKING_QA, "怎么炒菜不糊", history=[])
    assert out["answer"] == "锅要预热充分。"


def test_dispatch_chitchat(mock_chat):
    mock_chat.set_response("你好陛下，想吃啥？")
    out = dispatch(Intent.CHITCHAT, "你好", history=[])
    assert "陛下" in out["answer"]


def test_dispatch_recipe_passes_history_to_handler(mock_chat):
    """recipe handler 应能看到 history，让"调淡一点"这类引用落到上轮的菜上。"""
    mock_chat.set_response(json.dumps([_fake_recipe("宫保鸡丁")]))
    history = [
        {"role": "user", "content": "宫保鸡丁"},
        {"role": "assistant", "content": "为你生成了食谱：《宫保鸡丁》，主料 鸡胸肉、花生。"},
    ]
    dispatch(Intent.RECIPE, "调淡一点", history=history)
    sent = mock_chat.calls[0]["messages"]
    # 至少应包含 system + 上轮 user + 上轮 assistant + 本轮 user
    assert any(m["role"] == "assistant" and "宫保鸡丁" in m["content"] for m in sent)
    assert sent[-1] == {"role": "user", "content": "调淡一点"}
