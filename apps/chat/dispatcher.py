"""按 intent 分发到对应 handler，并提供历史摘要。"""
import time
from typing import Any

from apps.ingredient import handler as ingredient_handler
from apps.qa import handler as qa_handler
from apps.recipe import handler as recipe_handler
from apps.recommend import handler as recommend_handler
from core.llm import chat
from core.logging import get_logger

from .intents import Intent

logger = get_logger(__name__)


def _chitchat(user_input: str, history: list[dict] | None = None) -> dict:
    """兜底闲聊：保持 小厨 人设。"""
    messages = [{"role": "system", "content": "你是 小厨，做菜领域的 AI 助手。简洁友好回应用户的闲聊或不相关提问，并自然引导回做菜话题。"}]
    if history:
        messages.extend(history[-4:])
    messages.append({"role": "user", "content": user_input})
    return {"answer": chat(messages, max_tokens=300)}


def dispatch(intent: Intent, user_input: str, history: list[dict]) -> Any:
    """根据 intent 调用对应 handler，返回 data。"""
    logger.debug("分发 开始 intent=%s history_len=%d", intent.value, len(history or []))
    t0 = time.perf_counter()
    try:
        if intent == Intent.RECIPE:
            recipes = recipe_handler.handle(user_input)
            data = {"recipes": [r.model_dump() for r in recipes]}
        elif intent == Intent.RECOMMEND:
            data = recommend_handler.handle(user_input)
        elif intent == Intent.INGREDIENT:
            data = ingredient_handler.handle(user_input)
        elif intent == Intent.COOKING_QA:
            data = qa_handler.handle(user_input, history=history)
        else:
            data = _chitchat(user_input, history=history)
    except Exception:
        elapsed_ms = (time.perf_counter() - t0) * 1000
        logger.exception("分发 失败 intent=%s elapsed_ms=%.0f", intent.value, elapsed_ms)
        raise

    elapsed_ms = (time.perf_counter() - t0) * 1000
    logger.info("分发 完成 intent=%s elapsed_ms=%.0f", intent.value, elapsed_ms)
    return data


def summarize(intent: Intent, data: dict) -> str:
    """把 data 转成自然语言摘要，写入 history 让多轮上下文连贯。"""
    if intent == Intent.RECIPE:
        names = [r.get("dish_name", "") for r in data.get("recipes", [])]
        if not names:
            return "（未生成菜谱）"
        return f"为你生成了《{'》《'.join(names)}》的食谱。"

    if intent == Intent.RECOMMEND:
        dishes = data.get("dishes", [])
        detailed = [r.get("dish_name", "") for r in data.get("recipes", []) if "dish_name" in r]
        parts = []
        if dishes:
            parts.append(f"推荐了 {len(dishes)} 道菜：{'、'.join(dishes)}")
        if detailed:
            parts.append(f"已详细生成《{'》《'.join(detailed)}》的菜谱")
        return "。".join(parts) + "。" if parts else "（未推荐菜品）"

    if intent == Intent.INGREDIENT:
        dishes = data.get("dishes", [])
        return f"根据你的食材，可做：{'、'.join(dishes)}。" if dishes else "（未找到合适菜品）"

    # COOKING_QA / CHITCHAT
    return data.get("answer", "")
