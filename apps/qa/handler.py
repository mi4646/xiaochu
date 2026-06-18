"""烹饪问答处理器（占位实现）。"""
from collections.abc import Iterator

from core.llm import chat
from core.logging import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """你是 小厨 的烹饪问答模块。
用户询问烹饪技巧、原理、常识，请用简洁专业的语言回答。
回答控制在 200 字内，分点列出更易读。"""


def _build_messages(user_input: str, history: list[dict] | None) -> list[dict]:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        messages.extend(history[-6:])
    messages.append({"role": "user", "content": user_input})
    return messages


def handle(user_input: str, history: list[dict] | None = None) -> dict:
    logger.info("烹饪问答 开始 input=%r history_len=%d", user_input[:80], len(history or []))
    answer = chat(_build_messages(user_input, history), max_tokens=600)
    logger.info("烹饪问答 完成 chars=%d", len(answer))
    return {"answer": answer}


def handle_stream(user_input: str, history: list[dict] | None = None) -> Iterator[str]:
    """流式版本：返回字符串增量生成器。调用方负责拼接完整回答。"""
    logger.info("烹饪问答 开始-流式 input=%r history_len=%d", user_input[:80], len(history or []))
    return chat(_build_messages(user_input, history), max_tokens=600, stream=True)
