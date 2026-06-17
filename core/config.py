"""全局配置：从 .env 加载环境变量。"""
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置，自动从 .env 读取。

    使用 OpenAI 兼容协议，可对接 OpenAI / DeepSeek / 通义千问 / Moonshot 等任意服务。
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    openai_api_key: str = Field(..., description="API 密钥")
    openai_base_url: str = Field(
        default="https://api.openai.com/v1",
        description="API base_url，支持任意 OpenAI 协议兼容服务",
    )
    xiaochu_model: str = Field(default="gpt-4o-mini", description="模型名")
    xiaochu_host: str = Field(default="127.0.0.1", description="FastAPI 监听地址")
    xiaochu_port: int = Field(default=8000, description="FastAPI 监听端口")

    # 日志：详见 core/logging.py
    xiaochu_log_level: str = Field(default="INFO", description="DEBUG/INFO/WARNING/ERROR")
    xiaochu_log_dir: str = Field(default="logs", description="日志目录，相对项目根或绝对路径")
    xiaochu_log_to_console: bool = Field(default=True, description="是否同时输出到控制台")
    xiaochu_log_max_bytes: int = Field(default=5 * 1024 * 1024, description="单文件轮转大小（字节）")
    xiaochu_log_backup_count: int = Field(default=5, description="轮转保留份数")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """单例配置，全局复用。"""
    return Settings()
