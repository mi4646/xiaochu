"""烹饪问答处理器（占位实现）。"""
from core.llm import chat
from core.logging import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """你是 小厨 的烹饪问答模块。
用户询问烹饪技巧、原理、常识，请用简洁专业的语言回答。
回答控制在 200 字内，分点列出更易读。"""


def handle(user_input: str, history: list[dict] | None = None) -> dict:
    logger.info("烹饪问答 开始 input=%r history_len=%d", user_input[:80], len(history or []))
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        messages.extend(history[-6:])
    messages.append({"role": "user", "content": user_input})
    answer = chat(messages, max_tokens=600)
    logger.info("烹饪问答 完成 chars=%d", len(answer))
    return {"answer": answer}
