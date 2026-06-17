"""菜品推荐处理器：推荐菜名 + 并发生成详细菜谱。

策略：
- 用户没明说数量 → 详细生成 3 道
- 用户明说 N (N ≤ 7) → 详细生成 N 道
- 用户要求 > 7 → 详细生成 7 道，剩余仅名单 + 提示分批
"""
import json
from concurrent.futures import ThreadPoolExecutor

from apps.recipe import handler as recipe_handler
from core.llm import chat
from core.logging import get_logger

logger = get_logger(__name__)

DEFAULT_DETAIL_COUNT = 3
MAX_DETAIL_COUNT = 7

SYSTEM_PROMPT = """你是 小厨 的菜品推荐模块。
根据用户场景描述，给出菜品推荐，并判断用户期望详细看到几道菜。

输出严格 JSON（只输出 JSON 本身，不要 markdown 包裹）：
{
  "dishes": ["菜名1", "菜名2", ...],
  "desired_count": 3
}

字段说明：
- dishes: 推荐菜品名称数组，长度根据用户场景合理决定（一般 3-8 道）
- desired_count: 用户期望详细看到几道菜的菜谱
  · 用户明确说"N 菜一汤"/"推荐 N 道"/"N 个菜" → desired_count = N
  · 用户没明说数量 → desired_count = 3
  · 不要超过 dishes 数组长度

不要解释，只输出 JSON。
"""


def _parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.rsplit("```", 1)[0].strip()
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]
    return json.loads(text)


def handle(user_input: str) -> dict:
    """推荐菜名 + 并发生成详细菜谱。"""
    logger.info("菜品推荐 开始 input=%r", user_input[:80])
    raw = chat(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_input},
        ],
        max_tokens=400,
    )
    try:
        parsed = _parse_json(raw)
    except json.JSONDecodeError:
        logger.exception("菜品推荐 JSON解析失败 raw_head=%r", raw[:300])
        raise
    dishes: list[str] = [d.strip() for d in parsed.get("dishes", []) if d.strip()]
    desired = int(parsed.get("desired_count", DEFAULT_DETAIL_COUNT))

    # 限位：不超过 MAX、不超过 dishes 数量
    detail_count = min(max(desired, 1), MAX_DETAIL_COUNT, len(dishes))
    truncated = desired > MAX_DETAIL_COUNT
    logger.debug(
        "菜品推荐 限位 dishes=%d desired=%d detail_count=%d truncated=%s",
        len(dishes), desired, detail_count, truncated,
    )

    detail_targets = dishes[:detail_count]

    # 并发生成详细菜谱
    recipes: list[dict] = []
    if detail_targets:
        logger.info("菜品推荐 并发生成 count=%d 菜品=%s", len(detail_targets), detail_targets)
        with ThreadPoolExecutor(max_workers=detail_count) as pool:
            futures = [pool.submit(recipe_handler.handle, name) for name in detail_targets]
            for name, fut in zip(detail_targets, futures):
                try:
                    for r in fut.result():
                        recipes.append(r.model_dump())
                except Exception as e:  # noqa: BLE001
                    logger.exception("菜品推荐 子菜谱失败 name=%s", name)
                    recipes.append({"error": str(e)})

    note_parts = [f"已为你详细生成前 {len(recipes)} 道菜的菜谱。"]
    if len(dishes) > detail_count:
        note_parts.append(f"剩余 {len(dishes) - detail_count} 道仅列出名称。")
    if truncated:
        note_parts.append(f"为保证质量，单次最多详细生成 {MAX_DETAIL_COUNT} 道，可分批继续。")

    logger.info(
        "菜品推荐 完成 dishes=%d detailed=%d errors=%d",
        len(dishes), len(recipes), sum(1 for r in recipes if "error" in r),
    )
    return {
        "dishes": dishes,
        "recipes": recipes,
        "note": " ".join(note_parts),
    }
