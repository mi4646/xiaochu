"""统一日志配置：基于标准库 logging，文件轮转 + 控制台彩色（rich）。

所有模块通过 ``get_logger(__name__)`` 拿到 logger，调用前在入口处（main.py / cli.py /
pytest 视需要）调一次 ``setup_logging()`` 完成全局配置。多次调用会被幂等地跳过。

落盘文件：
    <log_dir>/xiaochu.log       # 应用主日志（DEBUG 及以上，按大小轮转）
    <log_dir>/xiaochu.error.log # 仅错误（ERROR 及以上，按大小轮转）

设计取舍：
- 不引第三方日志库，stdlib + rich（项目已依赖）就够用
- 控制台输出走 RichHandler 美化，文件输出走纯文本，不带 ANSI
- uvicorn / fastapi 自带的日志通过 propagate 让根 logger 接管，统一格式
"""
from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

from rich.logging import RichHandler

from .config import get_settings

_FILE_FMT = "%(asctime)s [%(levelname)-7s] %(name)s :: %(message)s"
_DATE_FMT = "%Y-%m-%d %H:%M:%S"

_configured = False


def setup_logging(*, force: bool = False) -> None:
    """初始化全局日志配置。重复调用幂等，除非 ``force=True``。"""
    global _configured
    if _configured and not force:
        return

    s = get_settings()
    log_dir = Path(s.xiaochu_log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    level = getattr(logging, s.xiaochu_log_level.upper(), logging.INFO)

    root = logging.getLogger()
    root.setLevel(level)
    # 清掉已有 handler，避免重复输出（如 uvicorn 默认配置）
    for h in list(root.handlers):
        root.removeHandler(h)

    file_formatter = logging.Formatter(_FILE_FMT, _DATE_FMT)

    # 主日志：所有级别按大小轮转
    main_handler = logging.handlers.RotatingFileHandler(
        log_dir / "xiaochu.log",
        maxBytes=s.xiaochu_log_max_bytes,
        backupCount=s.xiaochu_log_backup_count,
        encoding="utf-8",
    )
    main_handler.setLevel(level)
    main_handler.setFormatter(file_formatter)
    root.addHandler(main_handler)

    # 错误日志：单独一份，便于线上 grep
    err_handler = logging.handlers.RotatingFileHandler(
        log_dir / "xiaochu.error.log",
        maxBytes=s.xiaochu_log_max_bytes,
        backupCount=s.xiaochu_log_backup_count,
        encoding="utf-8",
    )
    err_handler.setLevel(logging.ERROR)
    err_handler.setFormatter(file_formatter)
    root.addHandler(err_handler)

    # 控制台：可选，rich 渲染
    if s.xiaochu_log_to_console:
        console_handler = RichHandler(
            level=level,
            show_time=True,
            show_path=False,
            rich_tracebacks=True,
            markup=False,
        )
        console_handler.setFormatter(logging.Formatter("%(name)s :: %(message)s"))
        root.addHandler(console_handler)

    # 收敛过吵的第三方 logger（仍会记到文件，但默认不刷屏）
    for noisy in ("httpx", "httpcore", "openai"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _configured = True
    logging.getLogger(__name__).debug(
        "日志系统初始化 level=%s dir=%s console=%s",
        s.xiaochu_log_level, log_dir, s.xiaochu_log_to_console,
    )


def get_logger(name: str) -> logging.Logger:
    """模块内统一获取 logger。未 setup 时返回的 logger 仍可用，只是无 handler。"""
    return logging.getLogger(name)
