# 03. 开发 MCP Server：从最小可用到生产级

> 本文按"能跑 → 好用 → 可上线"三档讲清楚 MCP server 的开发：**Python/TypeScript SDK、tool/resource/prompt 设计、鉴权、错误处理、调试、打包发布**。读完你能写一个真正能给同事用的 MCP server。

---

## 一、技术栈选择

| 语言 | SDK | 何时选 |
|---|---|---|
| **Python** | `mcp[cli]` (FastMCP 内置) | 数据 / AI / 调用其他 Python 库居多 |
| **TypeScript / Node** | `@modelcontextprotocol/sdk` | 服务端、需要 npm 生态 |
| **Go** | `mcp-go` (社区，质量好) | 高性能、单二进制部署 |
| **Rust / Java / C#** | 社区 SDK | 集成进存量服务 |

> **首推 Python（FastMCP）**——3 行装饰器就能起一个 server，最适合上手。

---

## 二、Python：30 行写一个完整 server

### 2.1 安装

```bash
pip install "mcp[cli]"
```

### 2.2 最小 server

```python
# weather_server.py
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("weather-server")

@mcp.tool()
def get_weather(city: str, unit: str = "celsius") -> str:
    """查询指定城市当前的天气。

    Args:
        city: 城市名（中文全称，如 '北京'）
        unit: 温度单位 celsius / fahrenheit
    """
    # 这里实际可以调真实 API
    temp = 18 if unit == "celsius" else 64
    return f"{city} 当前 {temp}°{'C' if unit == 'celsius' else 'F'}，晴"

@mcp.resource("weather://history/{city}")
def get_history(city: str) -> str:
    """查询城市历史天气"""
    return f"{city} 过去 30 天平均气温 15°C..."

@mcp.prompt()
def daily_briefing(city: str) -> str:
    """生成城市每日气象简报 prompt"""
    return f"请基于工具查询 {city} 当前天气和近期趋势，生成 100 字简报。"

if __name__ == "__main__":
    mcp.run()  # 默认 stdio
```

### 2.3 跑起来

```bash
# 用 Inspector 调试（不进 client 也能测）
npx @modelcontextprotocol/inspector python weather_server.py

# 配置进 Claude Desktop:
# {
#   "mcpServers": {
#     "weather": {
#       "command": "python",
#       "args": ["/abs/path/weather_server.py"]
#     }
#   }
# }
```

### 2.4 FastMCP 的关键约定

```python
# 1. type hint 决定 inputSchema
@mcp.tool()
def f(name: str, age: int = 18) -> str:
    """函数 docstring 自动成为 description.
    
    参数 docstring 自动成为 parameter description（用 Google/NumPy 风格）。
    """

# 2. 返回值规则
#    - str  : 直接当 text content
#    - dict : 当 JSON 返回（自动 dumps）
#    - 抛异常 : 转成 isError=True 的 result，message 给 LLM

# 3. 异步也支持
@mcp.tool()
async def fetch_data(url: str) -> str:
    async with httpx.AsyncClient() as c:
        r = await c.get(url)
        return r.text
```

---

## 三、TypeScript：完整 server 模板

### 3.1 安装

```bash
npm init -y
npm i @modelcontextprotocol/sdk zod
```

### 3.2 server 代码

```typescript
// src/index.ts
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

const server = new McpServer({
  name: "weather-server",
  version: "0.1.0",
});

server.tool(
  "get_weather",
  "查询指定城市当前的天气",
  {
    city: z.string().describe("城市名"),
    unit: z.enum(["celsius", "fahrenheit"]).default("celsius"),
  },
  async ({ city, unit }) => {
    const temp = unit === "celsius" ? 18 : 64;
    return {
      content: [{ type: "text", text: `${city} 当前 ${temp}°，晴` }],
    };
  },
);

server.resource(
  "weather-history",
  "weather://history/{city}",
  async (uri, { city }) => ({
    contents: [{ uri: uri.href, text: `${city} 历史数据...` }],
  }),
);

const transport = new StdioServerTransport();
await server.connect(transport);
```

### 3.3 打包

```json
// package.json
{
  "name": "@your-org/mcp-server-weather",
  "version": "0.1.0",
  "bin": { "mcp-server-weather": "./dist/index.js" },
  "scripts": { "build": "tsc" }
}
```

发布 npm 后，用户可以直接：

```json
{
  "mcpServers": {
    "weather": {
      "command": "npx",
      "args": ["-y", "@your-org/mcp-server-weather"]
    }
  }
}
```

---

## 四、Tool / Resource / Prompt 设计要点

### 4.1 Tool 的 LLM-Friendly Schema

```python
# ❌ 不好的
@mcp.tool()
def search(q: str, opts: dict) -> str:
    """search"""
```
LLM 不知道 `opts` 字段、不知道返回什么。

```python
# ✅ 好的
@mcp.tool()
def search_issues(
    repo: str,                            # owner/repo 格式
    query: str,                           # 关键词或 GitHub 搜索语法
    state: Literal["open", "closed", "all"] = "open",
    limit: int = 20,
) -> list[dict]:
    """搜索 GitHub 仓库的 issues。

    Args:
        repo: GitHub 仓库，格式 'owner/repo' 例如 'anthropics/claude-code'
        query: 关键词或 GitHub 搜索语法（支持 'is:bug', 'label:foo' 等）
        state: 'open' 仅未关闭 / 'closed' 已关闭 / 'all' 全部
        limit: 返回上限，默认 20，最多 100

    Returns:
        list of {number, title, state, url, body_preview}
    """
```

### 4.2 Tool 设计的 7 条原则

1. **小而专**：一个 tool 一件事，别做"万能 search"。
2. **参数有默认值**：减少 LLM 出错。
3. **enum 比 free-text 好**：能列举的就别让 LLM 自由发挥。
4. **明确返回结构**：dict 比 str 更好处理。
5. **错误信息可操作**：`"city '北京' 未找到，请尝试 '北京市'"`。
6. **副作用工具加确认参数**：`delete_file(path, confirm: bool = False)`。
7. **支持分页 / limit**：避免一次返回 10MB。

### 4.3 Resource 设计

Resource 是**只读、按 URI 定位、客户端可挂载**的数据源：

```python
@mcp.resource("docs://{section}")
def get_doc(section: str) -> str:
    return load_doc_file(section)

@mcp.resource("config://current")
def get_current_config() -> dict:
    return load_config()
```

URI 设计：
- 用**协议 + path** 形式（`docs://`、`postgres://`、`figma://`）
- **稳定、可分享**：同一 URI 不同时间内容可变，但语义稳定

### 4.4 Prompt 设计

把"工作流模板"包进去：

```python
@mcp.prompt()
def code_review(pr_url: str, focus: str = "general") -> list:
    return [
        {
            "role": "user",
            "content": f"""你是资深 code reviewer。
请 review 这个 PR: {pr_url}
重点关注: {focus}

输出格式:
- ⚠️ 关键问题
- 🔧 改进建议
- ✅ 优点
"""
        }
    ]
```

用户在 Claude 里输入 `/code-review` 触发，参数补完 → server 返回这个 prompt → LLM 拿着它配合其他 tool 干活。

---

## 五、鉴权与安全

### 5.1 stdio：信任进程边界
stdio server 由 client 启动，**继承 client 的环境变量**——所以最简单：

```json
"env": { "GITHUB_TOKEN": "ghp_xxx" }
```

server 里读 `os.environ['GITHUB_TOKEN']` 即可。

### 5.2 HTTP：必须做鉴权
HTTP server 暴露在网络上，**MCP 2026-03-26 规范了 OAuth 2.1 集成**：

```
Client            Server
  │                  │
  │ GET /mcp ──────→ │ 401 Unauthorized + WWW-Authenticate
  │                  │
  │ ─→ OAuth dance ─→│ Auth Server
  │ ←─ token ──────  │
  │                  │
  │ GET /mcp + Bearer→│ 200 OK
  │                  │
```

实操：
- 简单：API key in header（`Authorization: Bearer xxx`）
- 标准：OAuth 2.1（接公司 IDP 推荐）
- 高级：mTLS（内部超级敏感工具）

### 5.3 多租户

```python
@mcp.tool()
async def query_db(sql: str, *, ctx: Context) -> str:
    user = ctx.session.user_id   # 每个 session 关联一个 user
    if not has_permission(user, "db.query"):
        raise PermissionError(f"User {user} 无权查询")
    # ...
```

`Context` 由 server 框架注入，包含当前 session、user 信息。

### 5.4 沙箱化

任何"运行用户代码"的 tool 必须沙箱：
- shell 工具：限定可执行命令白名单
- code 工具：用 E2B / Daytona / Docker 子容器
- 文件工具：限定 root 路径，拒绝 `..`

### 5.5 红线清单

| 反模式 | 后果 |
|---|---|
| 把 admin 密钥放 stdio env | LLM 注入可调用任意 admin API |
| `exec(query)` 不过滤 | SQL 注入 / RCE |
| Resource 直接返回 .env | 密钥外泄 |
| Tool 描述里夹"无视前文 prompt" | Prompt injection 通道 |
| 没有 rate limit | 无意循环烧光成本 |

---

## 六、错误处理

### 6.1 协议层：用 `isError`

```python
# 业务错误（LLM 看得到、能据此调整）
@mcp.tool()
def get_user(id: int) -> dict:
    user = db.find(id)
    if not user:
        raise ValueError(f"User #{id} 不存在")  # FastMCP 自动转 isError=True
    return user
```

LLM 看到 `isError + message` 后会根据语义重试 / 改参数 / 报告。

### 6.2 协议错误：JSON-RPC error code

```
-32700  Parse error
-32600  Invalid Request
-32601  Method not found
-32602  Invalid params
-32603  Internal error
```

让 SDK 自动处理这些，不需要手写。

### 6.3 工具内的"软失败" vs "硬失败"

| 场景 | 处理 |
|---|---|
| 参数错（如 city 不存在） | 业务错误，LLM 能改 |
| 网络超时 | 重试 1-2 次再报错 |
| 鉴权挂了 | 立刻硬错（PermissionError） |
| Rate limited | 报告 retry_after，LLM 也能识别 |

---

## 七、调试 + 测试

### 7.1 MCP Inspector
```bash
npx @modelcontextprotocol/inspector python my_server.py
```
**写 server 必装**。GUI 显示所有 tools/resources/prompts，可手动调用。

### 7.2 单元测试

```python
import pytest
from mcp.server.fastmcp import FastMCP

@pytest.mark.asyncio
async def test_get_weather():
    from weather_server import mcp, get_weather
    result = get_weather("北京")
    assert "北京" in result
```

### 7.3 集成测试
用 SDK 自己当 client：

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_e2e():
    params = StdioServerParameters(command="python", args=["weather_server.py"])
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as session:
            await session.initialize()
            tools = await session.list_tools()
            assert any(t.name == "get_weather" for t in tools.tools)
            result = await session.call_tool("get_weather", {"city": "北京"})
            assert "晴" in result.content[0].text
```

---

## 八、生产化清单

```
□ 鉴权：API key / OAuth / mTLS
□ Rate limit：per-user / per-tool
□ Audit log：每次 tool call 落库
□ Error tracking：Sentry / 自建
□ Health check：HTTP 模式必须有 /health
□ 版本号：serverInfo.version 跟 git tag 一致
□ Schema 完整：required / description / enum 齐全
□ Description LLM 易懂：避免缩写、给例子
□ 工具数量 ≤ 30：太多 LLM 选不准
□ 文档：README + 一段 demo prompt
□ 容器化：Dockerfile / docker-compose
□ 监控：QPS / 延迟 / 错误率
□ 沙箱：所有"代码执行"路径
```

---

## 九、打包发布

### 9.1 Python (PyPI)

```toml
# pyproject.toml
[project]
name = "mcp-server-weather"
version = "0.1.0"
dependencies = ["mcp"]

[project.scripts]
mcp-server-weather = "weather_server:main"
```

```bash
pip install build twine
python -m build
twine upload dist/*
```

用户安装后配置：

```json
{
  "command": "uvx",
  "args": ["mcp-server-weather"]
}
```

### 9.2 TypeScript (npm)
见 §3.3。`npx -y @org/server-name` 是最常见入口。

### 9.3 Docker
```dockerfile
FROM python:3.11-slim
RUN pip install mcp httpx
COPY weather_server.py /app/
WORKDIR /app
CMD ["python", "weather_server.py"]
```

适合 HTTP / SSE 模式部署。

### 9.4 Cloudflare Workers / 类似 serverless
2026 年起 Cloudflare 提供 [Workers as MCP servers](https://developers.cloudflare.com/agents/model-context-protocol/) 一键模板。适合 HTTP server，免运维。

---

## 十、给 server 作者的 5 条经验

1. **先用 Python FastMCP 出 v0.1，能跑 → 再决定要不要换 TS/Go**。
2. **写 description 假装是给一个非英语母语者看**——简单、明确、举例。
3. **每个 tool 都先用 Inspector 手动跑一次**——schema 错最难发现。
4. **优先做"少而精"的工具**——10 个 well-described 工具 > 50 个混乱的。
5. **第一次发布前找一个新人挂上跑 Day 1**——你以为清楚的事情对 LLM 不一定。

---

下一篇：[04-industry-landscape.md](04-industry-landscape.md) — 业界生态、企业方案、安全治理、与 Function Calling/Plugin 的边界。
