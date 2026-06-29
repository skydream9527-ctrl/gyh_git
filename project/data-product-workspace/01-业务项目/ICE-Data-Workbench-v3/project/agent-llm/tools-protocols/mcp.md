# MCP（Model Context Protocol）：Agent 工具的"USB-C"

> **MCP** 是 Anthropic 在 2024 年 11 月推出的开源协议，目标是统一 LLM 应用与外部数据源、工具之间的连接方式。它的类比常用"AI 应用的 USB-C"——把"M 个应用 × N 个工具"的连接复杂度从 M×N 降到 M+N。

---

## 一、为什么 MCP 在 2024 年突然火起来

Function Calling（[function-calling.md](function-calling.md)）解决了"LLM 怎么调工具"，但工程上仍有大问题：

| 问题 | 现状（无 MCP） | 有 MCP 后 |
|---|---|---|
| 同一个工具（如 GitHub API）要给每个 LLM 应用各写一遍 | M×N 集成成本 | 写 1 次工具、所有客户端可用 |
| 工具的鉴权 / 状态 / Schema 各家自定义 | 没标准 | 协议统一 |
| Claude Desktop、Cursor、Cline 等 IDE 各自插件 | 互不兼容 | 同一个 server 多端复用 |
| 用户给 LLM 共享数据需要每次粘贴 | 体验差 | LLM 应用直接连资源 |

**MCP 出现后 6 个月内**：Anthropic 自家产品、Cursor、Cline、Continue、Zed、Claude Code、Windsurf 等十几个客户端原生支持；社区 server 数量过千。**这是因果而非偶然**——它解决的是真实工程痛点。

---

## 二、MCP 的架构

```
┌──────────────┐                     ┌──────────────┐
│              │                     │              │
│  MCP Client  │ ←──── 协议 ────→   │  MCP Server  │
│              │   stdio / SSE /     │              │
│ (LLM 应用)   │   HTTP / WS         │ (工具/数据源) │
│              │                     │              │
└──────────────┘                     └──────────────┘
   Claude Desktop                       GitHub server
   Cursor                                Postgres server
   Claude Code                           Slack server
   Cline                                  本地文件 server
   ...                                   ...
```

**两端各干各的**：

- **Client**（任何想用工具的 LLM 应用）：把 server 的工具/资源装进 LLM 上下文
- **Server**（任何能提供工具或数据的程序）：暴露能力，不关心是谁在用

中间是**标准协议**：JSON-RPC 风格的消息，定义好 handshake、能力发现、调用语义。

---

## 三、MCP Server 暴露的三类能力

```
┌────────────────────────────────────────────────────────────┐
│                                                            │
│   1. Tools           可调用的函数                           │
│      工具            如：search_issues, run_sql, send_email│
│      ↓                                                     │
│      Client 把它注册成 LLM 的 function call                 │
│                                                            │
│   2. Resources       可读取的数据                           │
│      资源            如：filesystem://path, postgres://    │
│      ↓                                                     │
│      Client 把这些"挂载"成 LLM 上下文，按需检索             │
│                                                            │
│   3. Prompts         预制提示模板                           │
│      提示模板        如：/review-pr, /generate-test        │
│      ↓                                                     │
│      用户在 Client 里通过 slash command 触发               │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

> **三类能力的设计思路**：Tools 是动作、Resources 是材料、Prompts 是工作流模板。这个三分法对应 Agent 的三种基础需求。

---

## 四、最小 MCP Server（Python）

官方 SDK 几行代码搞定：

```python
# server.py
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("weather-server")

@mcp.tool()
def get_weather(city: str, unit: str = "celsius") -> str:
    """查询指定城市当前的天气。
    
    Args:
        city: 城市名（中文全称，如 '北京'）
        unit: 温度单位 celsius / fahrenheit
    """
    # ...真实查询逻辑
    return f"{city} 当前 18 度，晴"

@mcp.resource("weather://history/{city}")
def get_history(city: str) -> str:
    """查询城市历史天气"""
    return f"{city} 历史数据..."

if __name__ == "__main__":
    mcp.run()  # 默认 stdio 传输
```

注册到 Claude Desktop / Claude Code：

```json
// ~/.claude/claude_desktop_config.json
{
  "mcpServers": {
    "weather": {
      "command": "python",
      "args": ["/path/to/server.py"]
    }
  }
}
```

重启 Claude Desktop，工具就能用了——LLM 自动看到 `get_weather` 这个 function。

---

## 五、传输层：stdio / SSE / HTTP

MCP 支持多种传输：

| 传输 | 用途 | 例子 |
|---|---|---|
| **stdio** | 本地子进程（最常用） | Claude Desktop 启动本地 server 进程 |
| **SSE** | 远程 + Server-Sent Events | 长连接、多客户端 |
| **HTTP** | REST 风格 | 简单服务端集成 |
| **WebSocket** | 全双工 | 实时性高的场景 |

**生产经验**：

- 单机本地工具：stdio（最简单，零配置）
- 团队共享 / 远端工具：SSE 或 HTTP
- 大型多用户系统：HTTP + 鉴权层

---

## 六、生态现状（2026 年 5 月视角）

### 客户端（消费方）

- **Anthropic 自家**：Claude Desktop、Claude Code、Anthropic API workbench
- **IDE / Coding Agent**：Cursor、Cline、Continue、Zed、Windsurf、Trae
- **聊天 / 工作流**：LibreChat、Open WebUI、各种自研

### 服务端（提供方）

官方 + 社区已有几百个 server：

| 类别 | 例子 |
|---|---|
| 文件系统 | filesystem, git |
| 数据库 | postgres, sqlite, mongodb, mysql |
| Git 平台 | github, gitlab |
| 通信 | slack, discord, gmail |
| 浏览器 | playwright, browserbase |
| 设计 / 协作 | figma, notion, linear, jira |
| 监控 / 数据 | sentry, datadog, posthog |
| 搜索 | brave-search, tavily, exa |

> **本工作区相关**：[memory/](../../../memory/) 引用的飞书 MCP server 就是这套协议下的实例。详见仓库根 [README.md](../../../README.md) 的飞书部分。

---

## 七、MCP vs Function Calling：什么关系

```
Function Calling     ↔  让 LLM 输出"调哪个工具"的结构化指令
MCP                  ↔  让"工具的定义和实现"标准化、可复用

Function Calling 是"调用机制"
MCP 是"工具供给市场"

正交关系：
  使用 MCP 的客户端，内部通常还是用 Function Calling 来跟 LLM 通信
  MCP server 暴露的工具会被翻译成模型期待的 function schema
```

→ **MCP 不替代 Function Calling，是它的上一层基础设施**。

---

## 八、为什么 MCP 是关键基建（产品视角）

### 1. 解锁"长尾工具"
- 不是每个团队都有资源给自己的工具写每个 IDE 的插件
- 写一个 MCP server 就能在 N 个客户端被用起来

### 2. 让"个人助理"成为可能
- 一个用户接入 GitHub MCP + Slack MCP + Notion MCP + 浏览器 MCP
- 任何符合 MCP 的 LLM 应用都能用他的全套数据 / 工具

### 3. 数据访问标准化
- 之前每个 LLM 应用要重复实现"连数据库 / 读文件 / 抓邮件"
- 现在"数据源"和"应用"解耦

### 4. 隐私 + 本地化友好
- 大量 server 是本地运行的（stdio）
- 用户数据可以不出本机就被 LLM 使用

### 5. 协议中立
- 任何 LLM 厂商都能接（已经有 OpenAI、Google 端的实验性支持）
- Anthropic 主导但开源治理

---

## 九、风险与限制

### 1. 安全
- MCP server 一旦被启用，LLM 几乎可以任意调用——**等同于把工具的执行权给了模型**
- 用户从社区下载未经审查的 server 是高风险（有人推过恶意 server）
- 必须信任 server 来源 + 沙箱 + 权限控制

### 2. 性能开销
- 每个 server 是独立进程，启动有开销
- 本地装太多 server 会拖慢 IDE 启动

### 3. 上下文膨胀
- 装了 20 个 server，每个 5-10 个工具 → 100+ 工具描述塞进 prompt
- 模型选错率上升，token 成本上升
- 解法：动态启用 + 工具检索（详见 [function-calling.md](function-calling.md)）

### 4. 调试困难
- 协议层、传输层、工具层任何一个出问题都难定位
- 推荐用 MCP Inspector 工具调试

---

## 十、实操建议

### 选 / 用 server 时
- 优先用 Anthropic 官方 + 知名社区 server
- 第三方 server 看星标 + 维护活跃度
- 重要场景自己写一个简单的 wrapper server

### 自己写 server 时
- 用 SDK（Python 的 `mcp`、TypeScript 的 `@modelcontextprotocol/sdk`），别手写协议
- 工具描述写得像写 [function-calling.md](function-calling.md) 里说的那样具体
- 一个 server 不要塞太多无关工具，按领域拆分

### 部署模式
- 本地工具：stdio + 子进程
- 团队共用：自建 SSE server + 鉴权
- 多团队：HTTP API gateway + per-team server

---

## 十一、Checklist

```
□ 1. 我用 MCP 是为了"统一接入"，还是只是想跟风？
□ 2. 我装了多少 server？是否做了懒加载 / 按需启动？
□ 3. 第三方 server 我审查过代码吗？
□ 4. 工具描述清楚到 LLM 不会错调？
□ 5. 危险操作（删文件、发消息）有二次确认？
□ 6. 团队多人共用时，鉴权和权限分离做了吗？
□ 7. 出错时有 trace（哪个 server / 哪个工具 / 哪个调用）？
```

---

## 十二、扩展阅读

- 本目录：[function-calling.md](function-calling.md)
- 相关：[../agents/react-and-variants.md](../agents/react-and-variants.md)、[../production/observability.md](../production/observability.md)
- 官方文档：https://modelcontextprotocol.io
- 官方规范：https://spec.modelcontextprotocol.io
- 官方 SDK（Python / TypeScript / Java）：https://github.com/modelcontextprotocol
- Awesome MCP（社区 server 列表）：https://github.com/punkpeye/awesome-mcp-servers
- Anthropic 公告（2024-11）：*Introducing the Model Context Protocol*
- 本仓库 [knowledge-base/AI-Agent/](../../../knowledge-base/AI-Agent/) 中可能有 MCP 相关沉淀
