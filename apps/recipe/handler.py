"""食谱处理器：支持单/多菜，由 LLM 自己识别拆分。"""
import json

from core.llm import chat
from core.logging import get_logger

from .schemas import RecipeResponse

logger = get_logger(__name__)

SYSTEM_PROMPT = """你是 小厨，专业中餐厨师 AI。
用户输入可能是一道菜或多道菜（如"宫保鸡丁+木须肉"），你必须输出 JSON 数组，每个元素是一道菜的完整食谱。

JSON 格式（严格）：
[
  {
    "dish_name": "菜名",
    "ingredients": [{"name": "食材名", "amount": "分量"}],
    "steps": [{"order": 1, "description": "操作描述"}],
    "tips": ["贴士1", "贴士2"],
    "nutrition": {
      "calories": "约 450 kcal/份",
      "difficulty": "简单|中等|困难",
      "cook_time": "约 30 分钟",
      "servings": "2 人份"
    }
  }
]

要求：
1. 即使只有一道菜，也输出长度为 1 的数组
2. 步骤详细到火候、时间、手法
3. 食材分量要精确
4. 贴士 3-5 条
5. 只输出 JSON 数组，前后无任何文字
"""


def _parse_json_array(text: str) -> list[dict]:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.rsplit("```", 1)[0].strip()
    start, end = text.find("["), text.rfind("]")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]
    return json.loads(text)


def handle(user_input: str) -> list[RecipeResponse]:
    """根据用户输入生成单/多道菜的食谱。"""
    logger.info("食谱生成 开始 input=%r", user_input[:80])
    raw = chat(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_input},
        ],
        max_tokens=4096,
    )
    try:
        data = _parse_json_array(raw)
    except json.JSONDecodeError:
        logger.exception("食谱生成 JSON解析失败 raw_head=%r", raw[:300])
        raise
    recipes = [RecipeResponse.model_validate(item) for item in data]
    logger.info("食谱生成 完成 count=%d names=%s", len(recipes), [r.dish_name for r in recipes])
    return recipes
