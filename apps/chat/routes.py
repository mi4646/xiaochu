"""聊天入口路由。"""
import time
import uuid

from fastapi import APIRouter, HTTPException

from core.logging import get_logger

from .dispatcher import dispatch, summarize
from .router import classify_intent
from .schemas import ChatRequest, ChatResponse
from .session import get_store

logger = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat_endpoint(req: ChatRequest) -> ChatResponse:
    """统一聊天入口：识别意图 → 分发处理 → 返回。"""
    rid = uuid.uuid4().hex[:8]
    store = get_store()
    sid = store.ensure(req.session_id)
    history = store.get(sid)

    logger.info(
        "聊天请求 开始 rid=%s sid=%s history_len=%d msg=%r",
        rid, sid[:8], len(history), req.message[:80],
    )

    t0 = time.perf_counter()
    try:
        intent = classify_intent(req.message, history=history)
        t1 = time.perf_counter()
        data = dispatch(intent, req.message, history=history)
        t2 = time.perf_counter()
    except Exception as e:  # noqa: BLE001
        logger.exception("聊天请求 失败 rid=%s sid=%s", rid, sid[:8])
        raise HTTPException(status_code=500, detail=f"处理失败：{e}") from e

    logger.info(
        "聊天请求 完成 rid=%s sid=%s intent=%s classify_ms=%.0f dispatch_ms=%.0f total_ms=%.0f",
        rid, sid[:8], intent.value,
        (t1 - t0) * 1000, (t2 - t1) * 1000, (t2 - t0) * 1000,
    )

    # 写入会话历史：assistant 内容用自然语言摘要，让多轮上下文连贯
    store.append(sid, "user", req.message)
    store.append(sid, "assistant", summarize(intent, data))

    return ChatResponse(session_id=sid, intent=intent, data=data)
