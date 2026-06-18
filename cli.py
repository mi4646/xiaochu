"""命令行入口：交互式多意图聊天。

用法:
    python cli.py                   # 进入交互模式（默认逐字流式 + 表格）
    python cli.py 宫保鸡丁            # 单次请求
    python cli.py 冰箱里有鸡蛋         # 单次请求
    python cli.py --no-stream 宫保鸡丁 # 关闭流式，立即一次性渲染

环境变量:
    XIAOCHU_CLI_STREAM=0            # 全局关闭流式（同 --no-stream）
    XIAOCHU_CLI_CHAR_DELAY_MS=20    # 调整逐字节奏（毫秒/字），默认 20
"""
import io
import os as _os
import sys
import time

# CLI 默认不把日志刷到控制台（避免和 rich 渲染串行），仅落到文件
_os.environ.setdefault("XIAOCHU_LOG_TO_CONSOLE", "0")

from rich.console import Console, Group
from rich.panel import Panel
from rich.prompt import Prompt
from rich.rule import Rule
from rich.table import Table

from apps.chat.dispatcher import dispatch, dispatch_stream, summarize
from apps.chat.intents import Intent
from apps.chat.router import classify_intent
from apps.chat.session import get_store
from core.logging import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)

console = Console()

# 流式控制：CLI 参数 --no-stream > 环境变量 XIAOCHU_CLI_STREAM=0 > 默认开
STREAM_DEFAULT = _os.environ.get("XIAOCHU_CLI_STREAM", "1") not in ("0", "false", "False")
CHAR_DELAY_MS = int(_os.environ.get("XIAOCHU_CLI_CHAR_DELAY_MS", "20"))


# --------- 原 rich 表格渲染（--no-stream 时使用） ---------

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

        console.print("[bold green]食材清单[/bold green]")
        ing_t = Table(show_header=True, header_style="bold magenta")
        ing_t.add_column("食材", style="cyan")
        ing_t.add_column("分量", style="white")
        for ing in r["ingredients"]:
            ing_t.add_row(ing["name"], ing["amount"])
        console.print(ing_t)
        console.print()

        console.print("[bold green]烹饪步骤[/bold green]")
        for step in r["steps"]:
            console.print(f"  [bold cyan]{step['order']}.[/bold cyan] {step['description']}")
        console.print()

        console.print("[bold green]烹饪小贴士[/bold green]")
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
    """按 intent 分支美化输出（非流式回退用）。"""
    if intent == Intent.RECIPE:
        _render_recipes(data.get("recipes", []))
    elif intent == Intent.RECOMMEND:
        _render_dish_list(data.get("dishes", []), "推荐菜品", data.get("note"))
        recipes = data.get("recipes", [])
        if recipes:
            console.print()
            console.rule("[bold yellow]详细菜谱[/bold yellow]", style="yellow")
            _render_recipes(recipes)
    elif intent == Intent.INGREDIENT:
        _render_dish_list(data.get("dishes", []), "可做的菜", data.get("note"))
    elif intent == Intent.COOKING_QA:
        _render_answer(data, "烹饪问答")
    else:
        _render_answer(data, "小厨")


# --------- 流式渲染：rich 渲染对象 → ANSI 字符串 → 逐字打印 ---------

def _build_stream_renderable(intent: Intent, data: dict):
    """构造与 render() 同款的 rich 渲染对象（Panel / Table），供流式逐字输出。"""
    if intent == Intent.RECIPE:
        recipes = data.get("recipes", [])
        items = []
        for idx, r in enumerate(recipes):
            if "error" in r:
                items.append(f"[red]生成失败：{r['error']}[/red]")
                continue
            if idx > 0:
                items.append(Rule(style="yellow"))
            items.append(Panel.fit(f"[bold yellow]{r['dish_name']}[/bold yellow]", border_style="yellow"))
            nut = r["nutrition"]
            tbl = Table(show_header=False, box=None, padding=(0, 2))
            tbl.add_row("[cyan]难度[/cyan]", nut["difficulty"])
            tbl.add_row("[cyan]用时[/cyan]", nut["cook_time"])
            tbl.add_row("[cyan]分量[/cyan]", nut["servings"])
            tbl.add_row("[cyan]热量[/cyan]", nut["calories"])
            items.append(tbl)
            items.append("")

            items.append("[bold green]食材清单[/bold green]")
            ing = Table(show_header=True, header_style="bold magenta")
            ing.add_column("食材", style="cyan")
            ing.add_column("分量", style="white")
            for i in r["ingredients"]:
                ing.add_row(i["name"], i["amount"])
            items.append(ing)
            items.append("")

            items.append("[bold green]烹饪步骤[/bold green]")
            for step in r["steps"]:
                items.append(f"  [bold cyan]{step['order']}.[/bold cyan] {step['description']}")
            items.append("")

            items.append("[bold green]烹饪小贴士[/bold green]")
            for tip in r["tips"]:
                items.append(f"  • {tip}")
            items.append("")
        return Group(*items)

    if intent == Intent.RECOMMEND:
        items = [""]
        items.append(f"[bold green]推荐菜品[/bold green]")
        for d in data.get("dishes", []):
            items.append(f"  • {d}")
        note = data.get("note")
        if note:
            items.append("")
            items.append(f"[dim]{note}[/dim]")
        recipes = data.get("recipes", [])
        if recipes:
            items.append("")
            items.append(Rule(style="yellow"))
            for r in recipes:
                items.append(Panel.fit(f"[bold yellow]{r['dish_name']}[/bold yellow]", border_style="yellow"))
                items.extend(_build_renderables_for_recipe(r))
        return Group(*items)

    if intent == Intent.INGREDIENT:
        items = [""]
        items.append(f"[bold green]可做的菜[/bold green]")
        for d in data.get("dishes", []):
            items.append(f"  • {d}")
        note = data.get("note")
        if note:
            items.append("")
            items.append(f"[dim]{note}[/dim]")
        return Group(*items)

    # QA / CHITCHAT 兜底（正常走 _stream_nl_answer）
    return Panel(data.get("answer", ""), title="小厨", border_style="cyan")


def _build_renderables_for_recipe(r: dict) -> list:
    """供 _build_stream_renderable 内部复用——单菜的营养+食材+步骤+贴士（不含 dish_name Panel）。"""
    items = []
    nut = r["nutrition"]
    tbl = Table(show_header=False, box=None, padding=(0, 2))
    tbl.add_row("[cyan]难度[/cyan]", nut["difficulty"])
    tbl.add_row("[cyan]用时[/cyan]", nut["cook_time"])
    tbl.add_row("[cyan]分量[/cyan]", nut["servings"])
    tbl.add_row("[cyan]热量[/cyan]", nut["calories"])
    items.append(tbl)
    items.append("")

    items.append("[bold green]食材清单[/bold green]")
    ing = Table(show_header=True, header_style="bold magenta")
    ing.add_column("食材", style="cyan")
    ing.add_column("分量", style="white")
    for i in r["ingredients"]:
        ing.add_row(i["name"], i["amount"])
    items.append(ing)
    items.append("")

    items.append("[bold green]烹饪步骤[/bold green]")
    for step in r["steps"]:
        items.append(f"  [bold cyan]{step['order']}.[/bold cyan] {step['description']}")
    items.append("")

    items.append("[bold green]烹饪小贴士[/bold green]")
    for tip in r["tips"]:
        items.append(f"  • {tip}")
    items.append("")
    return items


def _render_to_ansi(renderable) -> str:
    """将 rich 渲染对象输出为带 ANSI 色彩控制码的字符串。"""
    buf = io.StringIO()
    ansi_con = Console(file=buf, force_terminal=True, color_system="truecolor", highlight=False, width=console.width)
    ansi_con.print(renderable)
    return buf.getvalue()


def _typewriter_ansi(text: str, delay_ms: int = CHAR_DELAY_MS) -> None:
    """逐字打印 ANSI 字符串：转义序列一次性写出，文字字符 sleep。

    Console(file=StringIO) 输出的字符串中，ANSI 转义序列（\\x1b[...m 等）
    是控制字符集，不能拆开写。本函数用正则拆分，控制码整段吐出，文字逐字。
    """
    import re
    ansi_pattern = re.compile(r"(\x1b\[[0-9;]*[a-zA-Z])")
    parts = ansi_pattern.split(text)
    delay = delay_ms / 1000.0

    for i, part in enumerate(parts):
        if not part:
            continue
        if i % 2 == 1:  # 奇数位 = ANSI 转义序列
            sys.stdout.write(part)
            sys.stdout.flush()
        else:  # 偶数位 = 普通文本
            for ch in part:
                sys.stdout.write(ch)
                sys.stdout.flush()
                if delay > 0:
                    time.sleep(delay)


def _stream_nl_answer(intent: Intent, message: str, history: list[dict]) -> str:
    """自然语言意图（QA/CHITCHAT）走真 token 流式。"""
    title = "烹饪问答" if intent == Intent.COOKING_QA else "小厨"
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


# --------- 主流程 ---------

def _confirm_ambiguous_recipes(message: str, data: dict) -> bool:
    """RECIPE 多菜歧义时二次确认。返回 False 表示用户取消。

    单次模式（stdin 非 tty）下不阻塞，仅打印理解结果让用户能看到。
    """
    if not data.get("_ambiguous_multi"):
        return True
    names = [r.get("dish_name", "") for r in data.get("recipes", [])]
    console.print()
    console.print(
        f"[yellow]⚠ 我把「{message}」理解为这 {len(names)} 道菜：[/yellow]"
        f" [bold]{ '、'.join(names) }[/bold]"
    )
    if not sys.stdin.isatty():
        # 非交互（如 pipe/单次模式重定向）下不阻塞，提示后继续
        console.print("[dim](非交互模式，已自动继续。如需精准结果请用 + / 和 等分隔，或单独输入一道菜)[/dim]")
        return True
    try:
        ans = Prompt.ask("[cyan]继续渲染？[/cyan]", choices=["y", "n"], default="y")
    except (KeyboardInterrupt, EOFError):
        console.print()
        return False
    if ans == "n":
        console.print("[dim]已取消。请用 + / 和 等分隔多道菜，或单独输入一道菜名重试。[/dim]")
        return False
    return True


def handle_message(message: str, session_id: str, *, stream: bool) -> None:
    """处理一条消息：识别意图 → 分发 → 渲染（流式 or 表格）。"""
    store = get_store()
    history = store.get(session_id)

    logger.info("CLI请求 开始 sid=%s history_len=%d stream=%s msg=%r",
                session_id[:8], len(history), stream, message[:80])
    with console.status("[bold cyan]小厨 思考中...", spinner="dots"):
        intent = classify_intent(message, history=history)

    console.print(f"[dim]意图: {intent.value}[/dim]")

    if not stream:
        # 关闭流式：走原 spinner + 表格渲染
        with console.status("[bold cyan]小厨 生成中...", spinner="dots"):
            data = dispatch(intent, message, history=history)
        if not _confirm_ambiguous_recipes(message, data):
            return
        render(intent, data)
    elif intent in (Intent.COOKING_QA, Intent.CHITCHAT):
        # 自然语言：真 token 流式
        answer = _stream_nl_answer(intent, message, history)
        data = {"answer": answer}
    else:
        # JSON 类：先生成完整结果，再渲染到 ANSI 字符串后逐字打出
        with console.status("[bold cyan]小厨 生成中...", spinner="dots"):
            data = dispatch(intent, message, history=history)
        if not _confirm_ambiguous_recipes(message, data):
            # 用户拒绝：丢弃本轮 data，不写入 history（让用户能重输更明确的输入）
            return
        console.print()
        renderable = _build_stream_renderable(intent, data)
        ansi_text = _render_to_ansi(renderable)
        _typewriter_ansi(ansi_text)

    logger.info("CLI请求 完成 sid=%s intent=%s", session_id[:8], intent.value)

    store.append(session_id, "user", message)
    store.append(session_id, "assistant", summarize(intent, data))


def interactive_loop(session_id: str, *, stream: bool) -> None:
    """多轮交互模式。"""
    console.print(Panel.fit(
        "[bold yellow]小厨[/bold yellow] · 做菜 AI 助手\n"
        "[dim]输入菜名、推荐请求、食材、烹饪问题都可以\n"
        f"流式: {'开' if stream else '关'}（--no-stream / XIAOCHU_CLI_STREAM=0 可关闭）\n"
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
            handle_message(msg, session_id, stream=stream)
        except Exception as e:  # noqa: BLE001
            logger.exception("CLI交互模式 异常")
            console.print(f"[bold red]错误[/bold red]：{e}")
        console.print()


def _parse_args(argv: list[str]) -> tuple[bool, str]:
    """从 argv 抽出 --no-stream 标志，返回 (stream, message)。"""
    stream = STREAM_DEFAULT
    rest: list[str] = []
    for a in argv:
        if a == "--no-stream":
            stream = False
        elif a == "--stream":
            stream = True
        else:
            rest.append(a)
    return stream, " ".join(rest).strip()


def main() -> int:
    stream, msg = _parse_args(sys.argv[1:])
    sid = get_store().create()

    # 单次模式
    if msg:
        try:
            handle_message(msg, sid, stream=stream)
            return 0
        except Exception as e:  # noqa: BLE001
            logger.exception("CLI单次模式 异常")
            console.print(f"[bold red]错误[/bold red]：{e}")
            return 2

    # 交互模式
    interactive_loop(sid, stream=stream)
    return 0


if __name__ == "__main__":
    sys.exit(main())
