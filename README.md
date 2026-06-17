# 小厨 Xiaochu 🍳

做菜领域的 AI 助手 —— 用户自由输入，自动识别意图并给出对应回答。

## 支持的意图

| 意图 | 示例输入 | 输出 |
|------|---------|------|
| **recipe** | "宫保鸡丁"、"宫保鸡丁+木须肉" | 完整食谱（单/多菜） |
| **recommend** | "今晚两人吃什么"、"三菜一汤"、"推荐 5 道家常菜" | 推荐菜品列表 + 并发生成前 N 道详细菜谱（默认 3 道，最多 7 道） |
| **ingredient** | "冰箱里有鸡蛋番茄米饭" | 可做的菜列表 |
| **cooking_qa** | "怎么炒菜不糊锅"、"鸡肉怎么腌嫩" | 技巧问答（支持多轮追问） |
| **chitchat** | 其他闲聊 | 友好兜底 |

## 项目结构

```
chefly/                          # 目录名暂保留，详见底部「关于目录名」
├── apps/
│   ├── chat/                # 统一聊天入口
│   │   ├── routes.py        # POST /chat
│   │   ├── intents.py       # Intent 枚举
│   │   ├── router.py        # 意图识别（一次 LLM 调用）
│   │   ├── dispatcher.py    # 按 intent 分发 + 历史摘要
│   │   ├── session.py       # 内存会话存储
│   │   └── schemas.py       # ChatRequest / ChatResponse
│   ├── recipe/
│   │   ├── handler.py       # 单/多菜食谱生成
│   │   └── schemas.py       # Pydantic 数据模型
│   ├── recommend/handler.py # 推荐 + 并发生成菜谱
│   ├── ingredient/handler.py# 食材反查
│   └── qa/handler.py        # 烹饪问答
├── core/
│   ├── config.py            # .env 配置
│   └── llm.py               # 统一 OpenAI 兼容客户端
├── main.py                  # FastAPI 入口
├── cli.py                   # 命令行交互入口
├── tests/
├── requirements.txt
├── .env.example
└── .python-version          # pyenv 虚拟环境绑定
```

## 技术栈

- **AI 接口**：OpenAI 兼容协议（OpenAI / DeepSeek / 通义千问 / Moonshot 等任意服务）
- **Web**：FastAPI + Uvicorn
- **数据**：Pydantic v2
- **CLI**：Rich
- **配置**：pydantic-settings + python-dotenv

## 依赖

<!-- AUTO-GENERATED: derived from requirements.txt -->

| 包 | 版本约束 | 用途 |
|----|---------|------|
| `openai` | `>=1.50.0` | OpenAI 兼容协议 SDK |
| `fastapi` | `>=0.115.0` | Web 框架 |
| `uvicorn[standard]` | `>=0.32.0` | ASGI 服务器 |
| `pydantic` | `>=2.0.0` | 数据校验 |
| `pydantic-settings` | `>=2.0.0` | .env 配置加载 |
| `python-dotenv` | `>=1.0.0` | dotenv 解析 |
| `rich` | `>=13.0.0` | CLI 终端美化 |

<!-- /AUTO-GENERATED -->

## 环境变量

<!-- AUTO-GENERATED: derived from .env.example -->

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `OPENAI_API_KEY` | ✅ | — | LLM 服务 API 密钥 |
| `OPENAI_BASE_URL` | ❌ | `https://api.openai.com/v1` | OpenAI 兼容协议 base_url |
| `XIAOCHU_MODEL` | ❌ | `gpt-4o-mini` | 使用的模型名 |
| `XIAOCHU_HOST` | ❌ | `127.0.0.1` | FastAPI 监听地址 |
| `XIAOCHU_PORT` | ❌ | `8000` | FastAPI 监听端口 |
| `XIAOCHU_LOG_LEVEL` | ❌ | `INFO` | 日志级别（DEBUG/INFO/WARNING/ERROR）|
| `XIAOCHU_LOG_DIR` | ❌ | `logs` | 日志目录 |
| `XIAOCHU_LOG_TO_CONSOLE` | ❌ | `1` | 是否同时输出到控制台 |
| `XIAOCHU_LOG_MAX_BYTES` | ❌ | `5242880` | 单文件轮转大小（字节）|
| `XIAOCHU_LOG_BACKUP_COUNT` | ❌ | `5` | 轮转保留份数 |

<!-- /AUTO-GENERATED -->

常见 OpenAI 兼容服务参考：

| 服务      | OPENAI_BASE_URL                                          | 示例模型           |
|-----------|----------------------------------------------------------|--------------------|
| OpenAI    | https://api.openai.com/v1                                | gpt-4o-mini        |
| DeepSeek  | https://api.deepseek.com/v1                              | deepseek-chat      |
| 通义千问  | https://dashscope.aliyuncs.com/compatible-mode/v1        | qwen-plus          |
| Moonshot  | https://api.moonshot.cn/v1                               | moonshot-v1-8k     |

## 环境准备

项目已绑定 pyenv 虚拟环境（Python 3.12.13），进入项目目录自动激活。

```bash
cd /var/www/chefly
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env，填入真实 OPENAI_API_KEY / OPENAI_BASE_URL / XIAOCHU_MODEL
```

## 使用方式

### CLI 交互（推荐）

```bash
python cli.py                    # 进入多轮交互
python cli.py 宫保鸡丁           # 单次请求
python cli.py 今晚吃什么         # 自动识别为推荐 + 详细菜谱
python cli.py 冰箱里有鸡蛋番茄   # 自动识别为食材反查
```

输入 `:q` 或 Ctrl+C 退出。

### Web API

```bash
python main.py
```

启动后访问：
- 文档：http://127.0.0.1:8000/docs
- 接口：`POST /chat`，body：`{"message": "...", "session_id": "可选"}`

## API 参考

<!-- AUTO-GENERATED: derived from FastAPI routes -->

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/chat` | 统一聊天入口（自动识别意图分发） |
| `GET` | `/` | 健康检查 |

<!-- /AUTO-GENERATED -->

### `POST /chat` 请求

```json
{
  "message": "宫保鸡丁+木须肉",
  "session_id": "可选，不传则自动创建"
}
```

### `POST /chat` 响应

统一壳：

```json
{
  "session_id": "abc123...",
  "intent": "recipe | recommend | ingredient | cooking_qa | chitchat",
  "data": { ... 按 intent 不同结构不同 ... }
}
```

按 `intent` 不同的 `data` 结构：

#### `intent = recipe`

```json
{
  "recipes": [
    {
      "dish_name": "宫保鸡丁",
      "ingredients": [{"name": "鸡腿肉", "amount": "300g"}],
      "steps": [{"order": 1, "description": "..."}],
      "tips": ["..."],
      "nutrition": {
        "calories": "约 450 kcal/份",
        "difficulty": "中等",
        "cook_time": "约 30 分钟",
        "servings": "2 人份"
      }
    }
  ]
}
```

#### `intent = recommend`

```json
{
  "dishes": ["番茄炒蛋", "凉拌黄瓜", "紫菜蛋花汤"],
  "recipes": [ /* 与 recipe 同结构，前 N 道详细菜谱 */ ],
  "note": "已为你详细生成前 3 道菜的菜谱。"
}
```

#### `intent = ingredient`

```json
{
  "dishes": ["番茄炒蛋", "蒸蛋羹", "..."],
  "note": "调用 /chat 并发送菜名可继续生成完整菜谱"
}
```

#### `intent = cooking_qa` / `chitchat`

```json
{ "answer": "..." }
```

## 多轮对话

CLI 交互模式与 Web 接口都支持会话上下文：传 `session_id` 即可携带历史，让"调淡一点"、"再来一道"、"第二点能详细说说吗"这类引用生效。

每轮 assistant 回复以**自然语言摘要**写入 history（而非 JSON），保证 LLM 在后续轮次能正确指代上文。

## 推荐 + 菜谱并发策略

| 用户场景 | 详细生成几道菜谱 |
|---------|----------------|
| 没明说数量（"今晚吃什么"） | 默认 3 道 |
| 明说 N（N ≤ 7） | 生成 N 道 |
| 明说 N（N > 7） | 仍只生成前 7 道，note 提示分批 |

实现：LLM 推荐时同时返回 `desired_count`，handler 用 `ThreadPoolExecutor` 并发调 recipe handler 生成前 N 道完整菜谱；单道失败不影响其他。

## 架构原则

- **不引入 agent 框架**（LangChain / LangGraph 暂不需要）：纯 Python + OpenAI SDK 已足够
- **意图分发**：先识别再处理，handler 职责单一
- **会话存储**：起步用内存 dict，后续可换 SQLite/Redis
- **历史摘要**：assistant 回复以自然语言进 history，让多轮上下文对 LLM 可读

## 测试

64 个 pytest 用例，全 mock LLM，约 1 秒跑完。

```bash
pip install -r requirements-dev.txt
python -m pytest
```

详见 [docs/TESTING.md](docs/TESTING.md)。

## 关于目录名 / pyenv 虚拟环境

项目品牌从 `Chefly` 更名为 `小厨 / Xiaochu` 后，**代码、配置、文档已全部同步**，但以下两项暂时保留旧名（改动牵涉系统配置，需独立维护窗口处理）：

- 工作目录仍为 `/var/www/chefly`
- pyenv 虚拟环境名仍为 `chefly`

未来若要彻底改名：

```bash
# 1. 重建 pyenv 虚拟环境
pyenv virtualenv 3.12.13 xiaochu
cd /var/www/chefly && pyenv local xiaochu
pip install -r requirements.txt -r requirements-dev.txt

# 2. 改目录（停服后）
sudo mv /var/www/chefly /var/www/xiaochu
# 同步更新 nginx / systemd / 启动脚本里的路径
```
