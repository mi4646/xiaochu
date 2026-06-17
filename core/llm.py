"""统一的 LLM 调用封装：所有 handler 走这里。"""
import time

from openai import OpenAI

from .config import get_settings
from .logging import get_logger

logger = get_logger(__name__)

_client: OpenAI | None = None


def get_client() -> OpenAI:
    """单例 OpenAI 兼容客户端。"""
    global _client
    if _client is None:
        s = get_settings()
        logger.debug("初始化OpenAI客户端 base_url=%s model=%s", s.openai_base_url, s.xiaochu_model)
        _client = OpenAI(api_key=s.openai_api_key, base_url=s.openai_base_url)
    return _client


def chat(
    messages: list[dict],
    *,
    model: str | None = None,
    max_tokens: int = 4096,
    stream: bool = False,
):
    """同步 / 流式 chat 调用。

    - stream=False: 返回拼接后的字符串
    - stream=True:  返回字符串增量生成器
    """
    s = get_settings()
    real_model = model or s.xiaochu_model
    msg_count = len(messages)
    last_role = messages[-1]["role"] if messages else "?"

    logger.debug(
        "调用LLM 开始 model=%s msgs=%d last_role=%s max_tokens=%d stream=%s",
        real_model, msg_count, last_role, max_tokens, stream,
    )
    t0 = time.perf_counter()
    try:
        completion = get_client().chat.completions.create(
            model=real_model,
            messages=messages,
            max_tokens=max_tokens,
            stream=stream,
        )
    except Exception:
        elapsed_ms = (time.perf_counter() - t0) * 1000
        logger.exception(
            "调用LLM 失败 model=%s msgs=%d elapsed_ms=%.0f",
            real_model, msg_count, elapsed_ms,
        )
        raise

    if not stream:
        text = (completion.choices[0].message.content or "").strip()
        elapsed_ms = (time.perf_counter() - t0) * 1000
        usage = getattr(completion, "usage", None)
        logger.info(
            "调用LLM 完成 model=%s msgs=%d elapsed_ms=%.0f resp_chars=%d%s",
            real_model, msg_count, elapsed_ms, len(text),
            f" tokens={usage.prompt_tokens}+{usage.completion_tokens}" if usage else "",
        )
        return text

    elapsed_ms = (time.perf_counter() - t0) * 1000
    logger.info("调用LLM 完成-流式 model=%s msgs=%d open_ms=%.0f", real_model, msg_count, elapsed_ms)

    def _gen():
        for chunk in completion:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                yield delta

    return _gen()
