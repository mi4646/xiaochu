"""意图识别：一次 LLM 调用，把用户输入映射到 Intent 枚举。"""
from core.llm import chat
from core.logging import get_logger

from .intents import Intent

logger = get_logger(__name__)

ROUTER_SYSTEM_PROMPT = """你是 小厨 的意图识别模块。
根据用户输入，从下面 5 个意图中选一个，只输出意图名（小写英文，无任何其他文字）：

- recipe：用户想要某道菜或几道菜的食谱（如"宫保鸡丁"、"红烧肉怎么做"、"宫保鸡丁+木须肉"）
- recommend：用户让你推荐菜（如"今晚吃什么"、"推荐三菜一汤"、"两人晚餐"）
- ingredient：用户给食材让你出菜（如"冰箱里有鸡蛋番茄"、"用鸡腿能做什么"）
- cooking_qa：烹饪技巧/常识问答（如"怎么炒菜不糊"、"鸡肉怎么腌嫩"、"为什么我的红烧肉发柴"）
- chitchat：以上都不符合的闲聊兜底

只输出意图名本身，不要解释、不要标点、不要多余字符。
"""


def classify_intent(user_input: str, history: list[dict] | None = None) -> Intent:
    """识别意图。失败时兜底为 CHITCHAT。"""
    messages = [{"role": "system", "content": ROUTER_SYSTEM_PROMPT}]
    # 带上少量历史让多轮"调淡一点"之类的引用能正确分类
    if history:
        messages.extend(history[-4:])
    messages.append({"role": "user", "content": user_input})

    raw = chat(messages, max_tokens=20).strip().lower()
    # 容错：取第一行第一个词
    cleaned = raw.splitlines()[0].split()[0] if raw else ""

    try:
        intent = Intent(cleaned)
        logger.info(
            "意图识别 完成 intent=%s input=%r history_len=%d",
            intent.value, user_input[:80], len(history or []),
        )
        return intent
    except ValueError:
        logger.warning(
            "意图识别 兜底CHITCHAT raw=%r cleaned=%r input=%r",
            raw, cleaned, user_input[:80],
        )
        return Intent.CHITCHAT
