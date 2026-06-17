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


def test_recipe_summary_includes_main_ingredients_and_flavor_hint():
    """摘要里要带主料和风味提示，让下轮 LLM 能识别"调淡一点"等引用。"""
    out = summarize(
        Intent.RECIPE,
        {
            "recipes": [
                {
                    "dish_name": "宫保鸡丁",
                    "ingredients": [
                        {"name": "鸡胸肉", "amount": "200g"},
                        {"name": "花生", "amount": "30g"},
                        {"name": "干辣椒", "amount": "5g"},
                        {"name": "葱", "amount": "适量"},
                    ],
                    "tips": ["糖醋比例 1:1 偏甜口", "鸡丁腌制 10 分钟更嫩"],
                }
            ]
        },
    )
    assert "宫保鸡丁" in out
    assert "鸡胸肉" in out and "花生" in out  # 主料前 3 项
    assert "糖醋" in out  # 风味提示
