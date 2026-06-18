"""按 intent 分发到对应 handler，并提供历史摘要。"""
import time
from collections.abc import Iterator
from typing import Any

from apps.ingredient import handler as ingredient_handler
from apps.qa import handler as qa_handler
from apps.recipe import handler as recipe_handler
from apps.recommend import handler as recommend_handler
from core.llm import chat
from core.logging import get_logger

from .intents import Intent

logger = get_logger(__name__)


def _chitchat_messages(user_input: str, history: list[dict] | None) -> list[dict]:
    messages = [{"role": "system", "content": "你是 小厨，做菜领域的 AI 助手。简洁友好回应用户的闲聊或不相关提问，并自然引导回做菜话题。"}]
    if history:
        messages.extend(history[-4:])
    messages.append({"role": "user", "content": user_input})
    return messages


def _chitchat(user_input: str, history: list[dict] | None = None) -> dict:
    """兜底闲聊：保持 小厨 人设。"""
    return {"answer": chat(_chitchat_messages(user_input, history), max_tokens=300)}


def _chitchat_stream(user_input: str, history: list[dict] | None = None) -> Iterator[str]:
    return chat(_chitchat_messages(user_input, history), max_tokens=300, stream=True)


def dispatch(intent: Intent, user_input: str, history: list[dict]) -> Any:
    """根据 intent 调用对应 handler，返回 data。"""
    logger.debug("分发 开始 intent=%s history_len=%d", intent.value, len(history or []))
    t0 = time.perf_counter()
    try:
        if intent == Intent.RECIPE:
            recipes, ambiguous_multi = recipe_handler.handle_with_meta(user_input, history=history)
            data = {"recipes": [r.model_dump() for r in recipes]}
            if ambiguous_multi:
                # 仅给 CLI 用的元字段，summarize 与 HTTP 客户端会忽略
                data["_ambiguous_multi"] = True
        elif intent == Intent.RECOMMEND:
            data = recommend_handler.handle(user_input, history=history)
        elif intent == Intent.INGREDIENT:
            data = ingredient_handler.handle(user_input, history=history)
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


def dispatch_stream(intent: Intent, user_input: str, history: list[dict]) -> Iterator[str] | None:
    """流式分发：仅 COOKING_QA / CHITCHAT 返回字符串增量生成器，其他 intent 返回 None。

    JSON 类 intent（RECIPE/RECOMMEND/INGREDIENT）必须等完整结果做 Pydantic 校验，
    无法逐字流式，调用方应回退到同步 dispatch。
    """
    if intent == Intent.COOKING_QA:
        return qa_handler.handle_stream(user_input, history=history)
    if intent == Intent.CHITCHAT:
        return _chitchat_stream(user_input, history=history)
    return None


def _recipe_brief(recipe: dict) -> str:
    """从单道菜的 dict 抽出"菜名（主料）"片段，让下轮 LLM 能识别引用。

    口味没有独立 schema 字段，用 tips 首条作为侧写（如"少放盐""偏甜"等）。
    """
    name = recipe.get("dish_name", "")
    ingredients = recipe.get("ingredients") or []
    mains = "、".join(i.get("name", "") for i in ingredients[:3] if i.get("name"))
    tips = recipe.get("tips") or []
    flavor = tips[0] if tips else ""
    parts = [f"《{name}》"] if name else []
    if mains:
        parts.append(f"主料 {mains}")
    if flavor:
        parts.append(f"风味提示 {flavor}")
    return "，".join(parts)


def summarize(intent: Intent, data: dict) -> str:
    """把 data 转成自然语言摘要，写入 history 让多轮上下文连贯。"""
    if intent == Intent.RECIPE:
        recipes = data.get("recipes", [])
        if not recipes:
            return "（未生成菜谱）"
        briefs = [_recipe_brief(r) for r in recipes]
        return f"为你生成了食谱：{'；'.join(briefs)}。"

    if intent == Intent.RECOMMEND:
        dishes = data.get("dishes", [])
        recipes = data.get("recipes", [])
        detailed_briefs = [_recipe_brief(r) for r in recipes if "dish_name" in r]
        parts = []
        if dishes:
            parts.append(f"推荐了 {len(dishes)} 道菜：{'、'.join(dishes)}")
        if detailed_briefs:
            parts.append(f"已详细生成 {'；'.join(detailed_briefs)}")
        return "。".join(parts) + "。" if parts else "（未推荐菜品）"

    if intent == Intent.INGREDIENT:
        dishes = data.get("dishes", [])
        return f"根据你的食材，可做：{'、'.join(dishes)}。" if dishes else "（未找到合适菜品）"

    # COOKING_QA / CHITCHAT
    return data.get("answer", "")
