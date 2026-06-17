"""聊天接口 schema。"""
from typing import Any

from pydantic import BaseModel, Field

from .intents import Intent


class ChatRequest(BaseModel):
    """用户聊天请求。"""

    message: str = Field(..., min_length=1, max_length=2000, description="用户输入")
    session_id: str | None = Field(default=None, description="会话 ID，为空则自动创建")


class ChatResponse(BaseModel):
    """统一响应：用 type 区分不同 intent 的 data 结构。"""

    session_id: str = Field(..., description="会话 ID")
    intent: Intent = Field(..., description="识别到的意图")
    data: Any = Field(..., description="按 intent 不同结构不同")
