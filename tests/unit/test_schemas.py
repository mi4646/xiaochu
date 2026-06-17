"""Pydantic schemas 校验测试。"""
import pytest
from pydantic import ValidationError

from apps.chat.intents import Intent
from apps.chat.schemas import ChatRequest, ChatResponse
from apps.recipe.schemas import (
    Ingredient,
    NutritionInfo,
    RecipeRequest,
    RecipeResponse,
    Step,
)


def test_chat_request_minimum():
    req = ChatRequest(message="宫保鸡丁")
    assert req.message == "宫保鸡丁"
    assert req.session_id is None


def test_chat_request_empty_message_rejected():
    with pytest.raises(ValidationError):
        ChatRequest(message="")


def test_chat_request_too_long_message_rejected():
    with pytest.raises(ValidationError):
        ChatRequest(message="x" * 2001)


def test_chat_response_with_session_id():
    resp = ChatResponse(session_id="abc", intent=Intent.RECIPE, data={"recipes": []})
    assert resp.intent == Intent.RECIPE
    assert resp.data == {"recipes": []}


def test_recipe_request_min_length():
    with pytest.raises(ValidationError):
        RecipeRequest(dish_name="")


def test_recipe_response_full_construction():
    r = RecipeResponse(
        dish_name="番茄炒蛋",
        ingredients=[Ingredient(name="番茄", amount="2 个")],
        steps=[Step(order=1, description="切番茄")],
        tips=["少放糖"],
        nutrition=NutritionInfo(
            calories="约 300 kcal",
            difficulty="简单",
            cook_time="约 10 分钟",
            servings="2 人份",
        ),
    )
    assert r.dish_name == "番茄炒蛋"
    assert r.nutrition.difficulty == "简单"


def test_nutrition_invalid_difficulty_rejected():
    with pytest.raises(ValidationError):
        NutritionInfo(
            calories="100",
            difficulty="超级难",  # 不在 Literal 范围
            cook_time="10 分钟",
            servings="1 人",
        )
