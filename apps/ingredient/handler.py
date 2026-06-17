"""食材反查处理器（占位实现）。"""
from core.llm import chat
from core.logging import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """你是 小厨 的食材反查模块。
用户列出手头食材，你列出能做的 5-8 道菜（按可行性优先级）。
只输出菜名，每行一道，不要解释。"""


def handle(user_input: str) -> dict:
    logger.info("食材反查 开始 input=%r", user_input[:80])
    raw = chat(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_input},
        ],
        max_tokens=200,
    )
    dishes = [line.strip(" -•·.") for line in raw.splitlines() if line.strip()]
    logger.info("食材反查 完成 dishes=%d", len(dishes))
    return {"dishes": dishes, "note": "调用 /chat 并发送菜名可继续生成完整菜谱"}
