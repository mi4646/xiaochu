"""FastAPI 应用入口。"""
import uvicorn
from fastapi import FastAPI

from apps.chat.routes import router as chat_router
from core.config import get_settings
from core.logging import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)

app = FastAPI(title="小厨 Xiaochu", description="做菜领域的 AI 助手", version="0.2.0")
app.include_router(chat_router)


@app.get("/")
def root() -> dict:
    return {"app": "xiaochu", "version": "0.2.0", "status": "ok"}


if __name__ == "__main__":
    settings = get_settings()
    logger.info(
        "启动 小厨 host=%s port=%s model=%s",
        settings.xiaochu_host, settings.xiaochu_port, settings.xiaochu_model,
    )
    uvicorn.run("main:app", host=settings.xiaochu_host, port=settings.xiaochu_port, reload=True)
