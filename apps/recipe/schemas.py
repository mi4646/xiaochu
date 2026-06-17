"""食谱模块的 Pydantic 数据模型。"""
from typing import Literal

from pydantic import BaseModel, Field


class Ingredient(BaseModel):
    """单个食材。"""

    name: str = Field(..., description="食材名称")
    amount: str = Field(..., description="分量，如 '200g'、'2 勺'")


class Step(BaseModel):
    """单个烹饪步骤。"""

    order: int = Field(..., description="步骤序号，从 1 开始")
    description: str = Field(..., description="详细操作描述")


class NutritionInfo(BaseModel):
    """营养信息与难度评级。"""

    calories: str = Field(..., description="热量估算，如 '约 450 kcal/份'")
    difficulty: Literal["简单", "中等", "困难"] = Field(..., description="难度评级")
    cook_time: str = Field(..., description="烹饪用时，如 '约 30 分钟'")
    servings: str = Field(..., description="分量，如 '2 人份'")


class RecipeResponse(BaseModel):
    """完整食谱响应。"""

    dish_name: str = Field(..., description="菜名")
    ingredients: list[Ingredient] = Field(..., description="食材清单")
    steps: list[Step] = Field(..., description="详细步骤")
    tips: list[str] = Field(..., description="烹饪小贴士")
    nutrition: NutritionInfo = Field(..., description="营养与难度信息")


class RecipeRequest(BaseModel):
    """食谱请求。"""

    dish_name: str = Field(..., min_length=1, max_length=100, description="菜名")
