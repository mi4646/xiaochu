# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目定位

小厨（Xiaochu）是做菜领域的 **多意图 AI 助手**：用户自由文本输入 → 意图识别 → 分发到对应 handler。**不引入 LangChain / LangGraph 等 agent 框架**，纯 Python + OpenAI SDK 实现。

> 历史名 `Chefly` 已弃用。代码、配置、prompt、日志全部用 `小厨 / Xiaochu / xiaochu_*`。**唯独工作目录 `/var/www/chefly` 与 pyenv 虚拟环境名 `chefly` 暂未改**（涉及 nginx/systemd/pyenv 重建，单独维护窗口处理）。

## 常用命令

```bash
# 运行（pyenv 虚拟环境暂仍叫 chefly，进入目录自动激活，Python 3.12.13）
python main.py                       # 启动 FastAPI（默认 127.0.0.1:8000）
python cli.py                        # 进入多轮交互式 CLI
python cli.py 宫保鸡丁                # CLI 单次模式

# 测试（64 用例，全 mock LLM，约 1 秒跑完）
python -m pytest                     # 全跑
python -m pytest tests/unit/         # 只跑单元层
python -m pytest -k "recipe"         # 按关键字过滤
python -m pytest -v                  # 详细模式
python -m pytest -x                  # 第一个失败处停止

# 依赖
pip install -r requirements.txt -r requirements-dev.txt
```

环境变量见 `.env.example`：必填 `OPENAI_API_KEY`，`OPENAI_BASE_URL` 默认 OpenAI 官方，可换 DeepSeek / 通义千问 / Moonshot 等任意走 OpenAI 协议的服务。

## 高层架构

### 数据流（关键路径）

```
用户输入 → POST /chat 或 cli.py
            │
            ▼
    apps/chat/router.py        ← 1 次 LLM 调用做意图识别
    返回 Intent 枚举值
            │
            ▼
    apps/chat/dispatcher.py    ← 按 Intent 分发
            │
            ├─ RECIPE     → apps/recipe/handler.py     单/多菜统一为 list[RecipeResponse]
            ├─ RECOMMEND  → apps/recommend/handler.py  推荐 + ThreadPoolExecutor 并发生成菜谱
            ├─ INGREDIENT → apps/ingredient/handler.py
            ├─ COOKING_QA → apps/qa/handler.py         需要 history 参数
            └─ CHITCHAT   → dispatcher 内联 _chitchat
            │
            ▼
    apps/chat/dispatcher.summarize(intent, data)
    → 把 data 转**自然语言摘要**写入 session history
    （这点关键：JSON 写进 history 会让下轮 LLM 读着别扭，必须摘要）
            │
            ▼
    apps/chat/session.py 的内存 SessionStore
```

### 模块职责边界

| 层 | 路径 | 不能做什么 |
|---|------|-----------|
| **入口** | `main.py` / `cli.py` / `apps/chat/routes.py` | 不能直接调 LLM，必须经 dispatcher |
| **路由层** | `apps/chat/router.py` | 只做意图识别，不做业务 |
| **分发层** | `apps/chat/dispatcher.py` | 只编排，不实现 handler 逻辑 |
| **处理器** | `apps/{recipe,recommend,ingredient,qa}/handler.py` | 不感知 session、不感知 HTTP |
| **基础设施** | `core/llm.py` / `core/config.py` | 唯一允许 import OpenAI SDK 的地方 |

所有 handler 通过 `from core.llm import chat` 调 LLM，**这是测试 mock 的关键 hook**。

### 容错解析（LLM JSON 输出）

`recipe/handler.py` 的 `_parse_json_array` 与 `recommend/handler.py` 的 `_parse_json` 都有三道防线：
1. 剥离 markdown 代码块包裹（` ```json...``` `）
2. 截取首个 `{` / `[` 到末个 `}` / `]`，去除模型可能附加的解释文字
3. `json.loads` + Pydantic 校验

不要给 LLM 调用加 `response_format={"type": "json_object"}` —— 通义千问 / DashScope 等服务不支持，会 400。靠 system prompt + 这三道防线。

## 测试体系（关键约定）

`tests/conftest.py` 提供 `mock_chat` fixture，按模块路径替换 `chat` 函数。**新增 handler 模块时必须把它加到 `mock_chat` 的 `targets` 列表**，否则该模块的测试会真调 LLM。

`autouse` 的 `_clean_session_store` fixture 自动隔离每个测试的会话状态。

测试金字塔分三层：`tests/unit/`（纯函数）、`tests/integration/`（mock LLM）、`tests/api/`（TestClient）。详见 `docs/TESTING.md`。

## 行为约束（来自用户全局指令）

- **称呼用户为「陛下」**：所有回复必须以此称呼，non-negotiable
- **中文回复**
- **简单优先**：不引入 agent 框架、不做超出请求范围的"改进"
- **保留 superpowers**：`docs/superpowers/` 不进 git

## 常见误区（已踩过的坑）

1. **不要把 history 存 JSON**：assistant 角色的 history 必须经 `summarize()` 转自然语言，否则多轮"调淡一点""第二点能详细说说"等引用会失效。
2. **`response_format: json_object` 不通用**：通义千问等服务不支持，靠容错解析就够。
3. **agent tool / 子 agent 不能加速纯生成**：评估过，对小厨这种"输入→生成"任务反而更慢（详见 git 历史里关于性能优化的讨论）。**唯一有效的并发是按业务实体拆分**（如 recommend 并发为多道菜各调一次 LLM）。
4. **`uvicorn.run()` 没有"后台模式"参数**：前后台由 shell 控制（`nohup`、`systemd` 等），不是 uvicorn 本身。
5. **生产环境真的要后台跑**：用 systemd 或 `gunicorn -k uvicorn.workers.UvicornWorker`，不要靠 `python main.py &`。

## 待办（按当前讨论优先级）

- 持久化会话：内存 dict → SQLite
- 覆盖率工具：pytest-cov
- 真 LLM 烟测：`tests/smoke/` 用 marker 隔离
- CI：`.github/workflows/test.yml`
