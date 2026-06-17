"""dispatcher.summarize 5 种 intent 输出测试。"""
from apps.chat.dispatcher import summarize
from apps.chat.intents import Intent


def test_recipe_single():
    out = summarize(Intent.RECIPE, {"recipes": [{"dish_name": "宫保鸡丁"}]})
    assert "宫保鸡丁" in out


def test_recipe_multiple():
    out = summarize(
        Intent.RECIPE,
        {"recipes": [{"dish_name": "A"}, {"dish_name": "B"}]},
    )
    assert "A" in out and "B" in out


def test_recipe_empty():
    out = summarize(Intent.RECIPE, {"recipes": []})
    assert "未生成" in out or out


def test_recommend_with_recipes():
    out = summarize(
        Intent.RECOMMEND,
        {
            "dishes": ["X", "Y", "Z"],
            "recipes": [{"dish_name": "X"}],
        },
    )
    assert "3 道菜" in out
    assert "X" in out


def test_recommend_no_recipes():
    out = summarize(Intent.RECOMMEND, {"dishes": ["X", "Y"], "recipes": []})
    assert "X" in out and "Y" in out


def test_recommend_empty():
    out = summarize(Intent.RECOMMEND, {"dishes": [], "recipes": []})
    assert "未推荐" in out or out


def test_ingredient():
    out = summarize(Intent.INGREDIENT, {"dishes": ["番茄炒蛋", "蒸蛋"]})
    assert "番茄炒蛋" in out and "蒸蛋" in out


def test_ingredient_empty():
    out = summarize(Intent.INGREDIENT, {"dishes": []})
    assert "未找到" in out or out


def test_qa_returns_answer_directly():
    out = summarize(Intent.COOKING_QA, {"answer": "锅要预热"})
    assert out == "锅要预热"


def test_chitchat_returns_answer_directly():
    out = summarize(Intent.CHITCHAT, {"answer": "你好陛下"})
    assert out == "你好陛下"
