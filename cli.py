"""命令行入口：交互式多意图聊天。

用法:
    python cli.py                  # 进入交互模式
    python cli.py 宫保鸡丁          # 单次请求
    python cli.py 冰箱里有鸡蛋      # 单次请求
"""
import os as _os
import sys

# CLI 默认不把日志刷到控制台（避免和 rich 渲染串行），仅落到文件
_os.environ.setdefault("XIAOCHU_LOG_TO_CONSOLE", "0")

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from apps.chat.dispatcher import dispatch, dispatch_stream, summarize
from apps.chat.intents import Intent
from apps.chat.router import classify_intent
from apps.chat.session import get_store
from core.logging import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)

console = Console()


def _render_recipes(recipes: list[dict]) -> None:
    """渲染食谱列表（单/多菜统一）。"""
    for idx, r in enumerate(recipes):
        if "error" in r:
            console.print(f"[red]生成失败：{r['error']}[/red]")
            continue
        if idx > 0:
            console.print()
            console.rule(style="yellow")
        console.print()
        console.print(Panel.fit(
            f"[bold yellow]{r['dish_name']}[/bold yellow]",
            border_style="yellow",
        ))

        nut = r["nutrition"]
        info = Table(show_header=False, box=None, padding=(0, 2))
        info.add_row("[cyan]难度[/cyan]", nut["difficulty"])
        info.add_row("[cyan]用时[/cyan]", nut["cook_time"])
        info.add_row("[cyan]分量[/cyan]", nut["servings"])
        info.add_row("[cyan]热量[/cyan]", nut["calories"])
        console.print(info)
        console.print()

        console.print("[bold green]🥬 食材清单[/bold green]")
        ing_t = Table(show_header=True, header_style="bold magenta")
        ing_t.add_column("食材", style="cyan")
        ing_t.add_column("分量", style="white")
        for ing in r["ingredients"]:
            ing_t.add_row(ing["name"], ing["amount"])
        console.print(ing_t)
        console.print()

        console.print("[bold green]👨‍🍳 烹饪步骤[/bold green]")
        for step in r["steps"]:
            console.print(f"  [bold cyan]{step['order']}.[/bold cyan] {step['description']}")
        console.print()

        console.print("[bold green]💡 烹饪小贴士[/bold green]")
        for tip in r["tips"]:
            console.print(f"  • {tip}")
        console.print()


def _render_dish_list(dishes: list[str], title: str, note: str | None = None) -> None:
    console.print()
    console.print(f"[bold green]{title}[/bold green]")
    for d in dishes:
        console.print(f"  • {d}")
    if note:
        console.print()
        console.print(f"[dim]{note}[/dim]")
    console.print()


def _render_answer(data: dict, title: str) -> None:
    console.print()
    console.print(Panel(data.get("answer", ""), title=title, border_style="cyan"))
    console.print()


def render(intent: Intent, data: dict) -> None:
    """按 intent 分支美化输出。"""
    if intent == Intent.RECIPE:
        _render_recipes(data.get("recipes", []))
    elif intent == Intent.RECOMMEND:
        _render_dish_list(data.get("dishes", []), "🍽 推荐菜品", data.get("note"))
        recipes = data.get("recipes", [])
        if recipes:
            console.print()
            console.rule("[bold yellow]详细菜谱[/bold yellow]", style="yellow")
            _render_recipes(recipes)
    elif intent == Intent.INGREDIENT:
        _render_dish_list(data.get("dishes", []), "🥕 可做的菜", data.get("note"))
    elif intent == Intent.COOKING_QA:
        _render_answer(data, "👨‍🍳 烹饪问答")
    else:
        _render_answer(data, "💬 小厨")


def _stream_answer(intent: Intent, message: str, history: list[dict]) -> str:
    """流式打印自然语言回答，返回拼好的完整文本。

    用 sys.stdout 直写并 flush，避免 rich.Console 在 end='' 模式下缓冲、
    把流式 chunk 攒到末尾才一齐 dump。
    """
    title = "👨‍🍳 烹饪问答" if intent == Intent.COOKING_QA else "💬 小厨"
    console.print()
    console.print(f"[bold cyan]{title}[/bold cyan]")
    parts: list[str] = []
    for delta in dispatch_stream(intent, message, history):
        parts.append(delta)
        sys.stdout.write(delta)
        sys.stdout.flush()
    sys.stdout.write("\n\n")
    sys.stdout.flush()
    return "".join(parts).strip()


def handle_message(message: str, session_id: str) -> None:
    """处理一条消息：识别意图 → 分发 → 渲染。"""
    store = get_store()
    history = store.get(session_id)

    logger.info("CLI请求 开始 sid=%s history_len=%d msg=%r", session_id[:8], len(history), message[:80])
    with console.status("[bold cyan]小厨 思考中...", spinner="dots"):
        intent = classify_intent(message, history=history)

    console.print(f"[dim]意图: {intent.value}[/dim]")

    if intent in (Intent.COOKING_QA, Intent.CHITCHAT):
        answer = _stream_answer(intent, message, history)
        data = {"answer": answer}
    else:
        with console.status("[bold cyan]小厨 生成中...", spinner="dots"):
            data = dispatch(intent, message, history=history)
        render(intent, data)

    logger.info("CLI请求 完成 sid=%s intent=%s", session_id[:8], intent.value)

    store.append(session_id, "user", message)
    store.append(session_id, "assistant", summarize(intent, data))


def interactive_loop(session_id: str) -> None:
    """多轮交互模式。"""
    console.print(Panel.fit(
        "[bold yellow]小厨[/bold yellow] · 做菜 AI 助手\n"
        "[dim]输入菜名、推荐请求、食材、烹饪问题都可以\n"
        "输入 :q 或按 Ctrl+C 退出[/dim]",
        border_style="yellow",
    ))
    console.print()

    while True:
        try:
            msg = Prompt.ask("[bold cyan]你[/bold cyan]")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]再见，陛下[/dim]")
            return

        msg = msg.strip()
        if not msg:
            continue
        if msg in (":q", ":quit", "exit", "quit"):
            console.print("[dim]再见，陛下[/dim]")
            return

        try:
            handle_message(msg, session_id)
        except Exception as e:  # noqa: BLE001
            logger.exception("CLI交互模式 异常")
            console.print(f"[bold red]错误[/bold red]：{e}")
        console.print()


def main() -> int:
    sid = get_store().create()

    # 单次模式
    if len(sys.argv) > 1:
        msg = " ".join(sys.argv[1:]).strip()
        try:
            handle_message(msg, sid)
            return 0
        except Exception as e:  # noqa: BLE001
            logger.exception("CLI单次模式 异常")
            console.print(f"[bold red]错误[/bold red]：{e}")
            return 2

    # 交互模式
    interactive_loop(sid)
    return 0


if __name__ == "__main__":
    sys.exit(main())
