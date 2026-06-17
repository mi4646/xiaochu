# 小厨 Xiaochu 测试指南

本文档说明 小厨 项目的 pytest 测试体系：怎么跑、怎么写、怎么扩展。

## 快速上手

```bash
# 安装测试依赖
pip install -r requirements-dev.txt

# 跑全部测试（约 1 秒）
python -m pytest

# 详细模式
python -m pytest -v

# 只跑某层
python -m pytest tests/unit/
python -m pytest tests/integration/
python -m pytest tests/api/

# 按关键字过滤
python -m pytest -k "recipe"
python -m pytest -k "session"

# 失败时简短回溯
python -m pytest --tb=short

# 在第一个失败处停止
python -m pytest -x
```

## 测试金字塔

```
          ┌─ API 层 (1 文件 / 6 用例)
          │     端到端 HTTP，TestClient + mock LLM
          │
        ┌─┴─ 集成层 (3 文件 / 20 用例)
        │     单模块业务逻辑 + mock LLM
        │
      ┌─┴────── 单元层 (6 文件 / 38 用例)
      │         纯函数，零依赖
```

## 目录结构

```
tests/
├── conftest.py                       # 共享 fixture
│
├── unit/                             # 单元层（纯函数）
│   ├── test_intents.py               # Intent 枚举
│   ├── test_schemas.py               # Pydantic 模型校验
│   ├── test_session.py               # SessionStore CRUD
│   ├── test_summarize.py             # dispatcher.summarize 5 种 intent
│   ├── test_recipe_parse.py          # recipe handler 容错解析
│   └── test_recommend_parse.py       # recommend handler 容错解析
│
├── integration/                      # 集成层（mock LLM）
│   ├── test_router.py                # 意图识别 5 种 + 兜底
│   ├── test_dispatcher.py            # 五分支分发
│   └── test_recommend_handler.py     # 数量识别 / 上限 / 失败容错
│
└── api/                              # API 层（HTTP 端到端）
    └── test_chat_endpoint.py         # POST /chat 全链路
```

## 核心 fixture

### `mock_chat`

替换所有 handler / router / dispatcher 模块里的 `chat` 函数，让测试零成本可重复。

```python
def test_classify_recipe(mock_chat):
    mock_chat.set_response("recipe")            # 下次 chat() 返回这个串
    assert classify_intent("宫保鸡丁") == Intent.RECIPE


def test_dispatch_recommend(mock_chat):
    # 多次调用按顺序返回
    mock_chat.set_responses([
        '{"dishes": ["A","B"], "desired_count": 2}',  # 第 1 次：推荐
        '[{"dish_name": "A", ...}]',                   # 第 2 次：A 的菜谱
        '[{"dish_name": "B", ...}]',                   # 第 3 次：B 的菜谱
    ])
    out = dispatch(Intent.RECOMMEND, "推荐两道", history=[])
    # ...
```

`mock_chat.calls` 记录每次调用（messages + kwargs），用于断言上下文是否传对。

### `_clean_session_store`（autouse）

每个测试用例自动获得独立 `SessionStore`，避免互相污染。无需在测试代码中显式引用。

### 自动注入的环境变量

`conftest.py` 在导入时设置：

| 变量 | 值 |
|------|-----|
| `OPENAI_API_KEY` | `sk-test` |
| `OPENAI_BASE_URL` | `https://api.test/v1` |
| `XIAOCHU_MODEL` | `test-model` |

避免 `pydantic-settings` 因缺失环境变量而抛 `ValidationError`。

## 写新测试

### 单元层（纯函数）

不需要 fixture，直接 import 测：

```python
from apps.chat.intents import Intent

def test_my_pure_function():
    assert Intent("recipe") is Intent.RECIPE
```

### 集成层（涉及 LLM）

加 `mock_chat` 参数：

```python
def test_some_handler(mock_chat):
    mock_chat.set_response("LLM 假装返回的字符串")
    out = some_handler.handle("用户输入")
    assert out == ...
```

### API 层（HTTP 端到端）

用 `TestClient` + `mock_chat`：

```python
from fastapi.testclient import TestClient
from main import app

def test_my_endpoint(mock_chat):
    mock_chat.set_responses(["recipe", '[{"dish_name":"X",...}]'])
    client = TestClient(app)
    r = client.post("/chat", json={"message": "X"})
    assert r.status_code == 200
```

注意：`/chat` 一次请求会调 LLM 至少两次（意图识别 + handler），所以要 `set_responses([...])` 准备多个响应。

## 测试覆盖清单

### 已覆盖

| 关注点 | 测试位置 |
|--------|---------|
| Intent 枚举 5 个值 | `unit/test_intents.py` |
| Pydantic 校验（min_length / max_length / Literal） | `unit/test_schemas.py` |
| SessionStore CRUD + 不变性 | `unit/test_session.py` |
| summarize 5 种 intent 输出 | `unit/test_summarize.py` |
| LLM 输出含 markdown / 解释文字的容错 | `unit/test_recipe_parse.py`、`unit/test_recommend_parse.py` |
| 意图识别 5 种合法 + 兜底 + 历史传递 | `integration/test_router.py` |
| 五分支 dispatch + 单菜 / 多菜 | `integration/test_dispatcher.py` |
| recommend 数量识别 / 上限 7 / 单道失败容错 | `integration/test_recommend_handler.py` |
| `/chat` 完整链路 + session 复用 + 非法 session 处理 | `api/test_chat_endpoint.py` |
| 空 message 422 校验 | `api/test_chat_endpoint.py` |
| handler 异常返回 500 | `api/test_chat_endpoint.py` |

### 暂未覆盖（按需补）

- 真实 LLM 烟测（建议另建 `tests/smoke/` 用 marker 隔离）
- 多线程并发场景（recommend 的 ThreadPoolExecutor 内部行为）
- CLI 交互模式渲染逻辑

## 配置文件

### `pytest.ini`

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -ra --strict-markers
```

- `testpaths`：只在 `tests/` 下找测试
- `--strict-markers`：未注册的 marker 会报错（防拼写）
- `-ra`：summary 显示所有非 pass 状态

### `requirements-dev.txt`

```
pytest>=8.0.0
```

只保留必需依赖。后续如要加：

| 包 | 用途 |
|----|------|
| `pytest-cov` | 覆盖率报告 |
| `pytest-xdist` | 并行加速 |
| `pytest-mock` | 不需要（用 monkeypatch 已够） |
| `httpx` | 不需要（fastapi.testclient 已带） |

## 反模式（请勿这样做）

### ❌ 测试里直接调真 LLM

```python
def test_recipe():
    out = recipe_handler.handle("宫保鸡丁")  # 调真 API，要钱要时间
```

正确：用 `mock_chat` fixture。

### ❌ 在源码里加 `if testing: ...` 分支

测试不应改变业务代码。用 `monkeypatch` / `mock_chat` 在外部替换。

### ❌ 跨测试共享状态

`SessionStore` 已通过 `_clean_session_store` autouse 自动隔离，请勿手动持久化。

### ❌ 断言 LLM 输出文本

```python
def test_recipe_returns_correct_dish():
    out = handle("番茄炒蛋")
    assert "鸡蛋" in out["recipes"][0]["ingredients"]  # ❌ 依赖真 LLM
```

正确：用 `mock_chat.set_response(<已知 JSON>)`，然后断言**解析逻辑**而非内容。

## CI 集成示例

GitHub Actions：

```yaml
# .github/workflows/test.yml
name: tests
on: [push, pull_request]
jobs:
  pytest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt -r requirements-dev.txt
      - run: python -m pytest
```

不需要 `OPENAI_API_KEY` —— 测试期已被 mock。

## 排错

### `ModuleNotFoundError: No module named 'apps'`

确认在项目根目录跑：`python -m pytest`。
`conftest.py` 会把项目根加入 `sys.path`。

### `ValidationError: OPENAI_API_KEY field required`

测试期 `conftest.py` 已设默认值；如仍出现，说明导入顺序异常 —— 检查是否有测试文件在 `conftest.py` 加载前执行了 `from core.config import get_settings`。

### Mock 没生效（看到真 LLM 调用）

`mock_chat` 是按模块替换的：模块用 `from core.llm import chat` 后，`mock_chat` 替换的是该模块**已绑定的引用**。如果新增 handler 模块没在 `conftest.py` 的 `targets` 列表里，需要手动追加。
