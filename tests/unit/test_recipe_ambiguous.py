"""recipe handler 的多菜歧义检测测试。"""
import json

import pytest

from apps.recipe.handler import _user_dish_separators, handle_with_meta


@pytest.mark.parametrize("text,expected", [
    ("鸡丁肉丝", False),               # 无分隔
    ("宫保鸡丁", False),               # 单菜名
    ("宫保鸡丁+鱼香肉丝", True),       # +
    ("宫保鸡丁、鱼香肉丝", True),      # 中文顿号
    ("宫保鸡丁和鱼香肉丝", True),      # 和
    ("宫保鸡丁跟鱼香肉丝", True),      # 跟
    ("番茄炒蛋,青椒土豆丝", True),     # 半角逗号
    ("番茄炒蛋，青椒土豆丝", True),    # 全角逗号
    ("做一道宫保鸡丁", False),
])
def test_user_dish_separators(text, expected):
    assert _user_dish_separators(text) is expected


_RECIPE_GONGBAO = {
    "dish_name": "宫保鸡丁",
    "ingredients": [{"name": "鸡胸肉", "amount": "200g"}],
    "steps": [{"order": 1, "description": "切丁"}],
    "tips": ["少盐"],
    "nutrition": {"calories": "约 380 kcal/份", "difficulty": "中等",
                  "cook_time": "约 25 分钟", "servings": "2 人份"},
}

_RECIPE_YUXIANG = {
    "dish_name": "鱼香肉丝",
    "ingredients": [{"name": "猪里脊", "amount": "150g"}],
    "steps": [{"order": 1, "description": "切丝"}],
    "tips": ["热锅冷油"],
    "nutrition": {"calories": "约 360 kcal/份", "difficulty": "中等",
                  "cook_time": "约 20 分钟", "servings": "2 人份"},
}

_TWO_RECIPES_JSON = json.dumps([_RECIPE_GONGBAO, _RECIPE_YUXIANG])
_ONE_RECIPE_JSON = json.dumps([_RECIPE_GONGBAO])


def test_handle_with_meta_ambiguous_when_two_dishes_no_separator(mock_chat):
    """LLM 输出 2 道菜 + 用户输入无分隔符 → ambiguous_multi=True。"""
    mock_chat.set_response(_TWO_RECIPES_JSON)
    recipes, ambiguous = handle_with_meta("鸡丁肉丝")
    assert len(recipes) == 2
    assert ambiguous is True


def test_handle_with_meta_not_ambiguous_when_user_used_separator(mock_chat):
    """LLM 输出 2 道菜 + 用户输入有分隔符 → ambiguous_multi=False。"""
    mock_chat.set_response(_TWO_RECIPES_JSON)
    recipes, ambiguous = handle_with_meta("宫保鸡丁+鱼香肉丝")
    assert len(recipes) == 2
    assert ambiguous is False


def test_handle_with_meta_not_ambiguous_when_single_dish(mock_chat):
    """LLM 仅输出 1 道菜 → ambiguous_multi=False。"""
    mock_chat.set_response(_ONE_RECIPE_JSON)
    recipes, ambiguous = handle_with_meta("鸡丁肉丝")
    assert len(recipes) == 1
    assert ambiguous is False
