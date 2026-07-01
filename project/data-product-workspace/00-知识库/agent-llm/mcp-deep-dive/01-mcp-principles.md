# 01. MCP 原理深度解析

> 本文系统拆解 MCP 协议本身：**它解决什么问题、消息格式怎么走、生命周期、传输层、与 Function Calling 的边界**。读完你能在白板上画出 client/server 一次完整握手 + tool 调用的全流程。

---

## 一、为什么 Function Calling 不够，必须搞 MCP

Function Calling 解决了 "LLM 怎么调工具"，但工程上仍有大问题：

```
┌────────────────────────────────────────────────────────┐
│ M 个 LLM 应用 × N 个工具 = M × N 次集成                  │
├────────────────────────────────────────────────────────┤
│                                                        │
│   Claude Desktop ─→ GitHub API   (写一遍)              │
│   Cursor          ─→ GitHub API   (再写一遍)            │
│   Cline           ─→ GitHub API   (再再写一遍)          │
│   Zed             ─→ GitHub API   (再再再写一遍)        │
│                                                        │
│   每加一个工具或一个新客户端，集成成本线性增长             │
│                                                        │
└────────────────────────────────────────────────────────┘
```

MCP 把它压成 **M + N**：

```
┌────────────────────────────────────────────────────────┐
│                                                        │
│   M 个 Client         standardized protocol         N  │
│   (Claude Desktop,   ◄══════ MCP Spec ══════►   工具  │
│    Cursor, Cline...)                          (server) │
│                                                        │
└────────────────────────────────────────────────────────┘
```

**写一次 server，所有兼容 client 都能用**。这是 MCP 的核心商业逻辑。

---

## 二、协议骨架

MCP 基于 **JSON-RPC 2.0**——经过 20 年验证的通用 RPC 协议。Anthropic 没造新轮子。

### 2.1 一条 JSON-RPC 消息长什么样

```json
// 请求
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "get_weather",
    "arguments": {"city": "北京"}
  }
}

// 响应
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {"type": "text", "text": "北京 18°C 晴"}
    ],
    "isError": false
  }
}

// 通知（无 id，无 response）
{
  "jsonrpc": "2.0",
  "method": "notifications/cancelled",
  "params": {"requestId": 1}
}
```

3 类消息：**Request / Response / Notification**。

### 2.2 协议层次

```
┌────────────────────────────────────────────────────────┐
│  Application Logic    Tools / Resources / Prompts      │  ← 业务能力
├────────────────────────────────────────────────────────┤
│  Lifecycle            initialize → operating → shutdown│  ← 状态机
├────────────────────────────────────────────────────────┤
│  Message Framing      JSON-RPC 2.0                     │  ← 消息层
├────────────────────────────────────────────────────────┤
│  Transport            stdio / SSE / Streamable HTTP    │  ← 传输层
└────────────────────────────────────────────────────────┘
```

---

## 三、Lifecycle：握手到关闭的状态机

```
   Client                                       Server
     │                                            │
     │ ─── 1) initialize (capabilities) ─────→    │
     │                                            │
     │ ←─── 2) initialize result ─────────────    │
     │       (server capabilities)                │
     │                                            │
     │ ─── 3) notifications/initialized ─────→    │
     │                                            │
     │═══════════════ Operating ═════════════════ │
     │                                            │
     │ ←──── tools/list / resources/list ────────→│
     │ ←──── tools/call / resources/read ────────→│
     │ ←──── notifications/* (双向) ─────────────→│
     │                                            │
     │═══════════════ Shutdown ═════════════════  │
     │                                            │
     │ ─── shutdown ───────────────────────→     │
     │ ←──── ack ───────────────────────────     │
     │                                            │
   close                                        close
```

### 3.1 initialize：能力协商

最关键的一步——双方互相告知"我支持什么"：

```json
// Client → Server
{
  "method": "initialize",
  "params": {
    "protocolVersion": "2026-03-26",
    "capabilities": {
      "roots":    { "listChanged": true },
      "sampling": {},
      "elicitation": {}
    },
    "clientInfo": { "name": "claude-desktop", "version": "0.7.3" }
  }
}

// Server → Client
{
  "result": {
    "protocolVersion": "2026-03-26",
    "capabilities": {
      "tools":     { "listChanged": true },
      "resources": { "subscribe": true, "listChanged": true },
      "prompts":   { "listChanged": true },
      "logging":   {}
    },
    "serverInfo": { "name": "github", "version": "1.4.2" }
  }
}
```

**capabilities 字段决定了对方可调用哪些 method**——这是协议向前兼容的核心：新版本加新能力不会打挂旧版本。

### 3.2 Notifications/initialized
握手完成的"通话开始"信号。之后才能发业务请求。

### 3.3 Shutdown
HTTP/SSE 模式下用 `shutdown` 方法或 transport 层关连接；stdio 直接关 stream。

---

## 四、三类原语（Primitives）

MCP 把 server 能暴露的能力归为三类，对应 Agent 的三种基础需求。

### 4.1 Tools：可调用的函数

最常用，**完全等价于 LLM 能调的 function**。

```json
// tools/list 返回:
{
  "tools": [
    {
      "name": "get_weather",
      "description": "查询指定城市当前天气",
      "inputSchema": {
        "type": "object",
        "properties": {
          "city": { "type": "string", "description": "城市中文名" },
          "unit": { "type": "string", "enum": ["celsius", "fahrenheit"] }
        },
        "required": ["city"]
      }
    }
  ]
}

// tools/call 调用:
{ "method": "tools/call",
  "params": { "name": "get_weather", "arguments": {"city": "北京"} } }

// 返回:
{ "result": {
    "content": [{ "type": "text", "text": "18°C 晴" }],
    "isError": false
  } }
```

**Schema 用 JSON Schema**——和 OpenAI Function Calling 一致，client 可以无缝转换。

### 4.2 Resources：可读取的数据

资源是**有 URI 的、客户端可"挂载"到 LLM 上下文的数据源**。

```json
// resources/list 返回:
{
  "resources": [
    { "uri": "file:///workspace/README.md", "name": "项目 README", "mimeType": "text/markdown" },
    { "uri": "postgres://prod/users",       "name": "用户表",      "mimeType": "application/json" }
  ]
}

// resources/read 读取:
{ "method": "resources/read", "params": { "uri": "file:///..." } }

// 返回:
{ "result": { "contents": [{ "uri": "...", "text": "..." }] } }
```

**与 Tools 的区别**：

| 维度 | Tools | Resources |
|---|---|---|
| 触发方 | LLM 决定调用 | 用户/客户端决定挂载 |
| 副作用 | 可能有（写入、调用 API） | 只读 |
| 计费 | 一般按调用 | 按上下文 token |
| 适用 | 动作 | 材料 |

### 4.3 Prompts：预制提示模板

让 server 提供"slash command 模板"。

```json
{
  "prompts": [
    {
      "name": "code-review",
      "description": "对给定 PR 做 code review",
      "arguments": [
        {"name": "pr_url", "required": true}
      ]
    }
  ]
}
```

用户在 Claude Desktop 里输入 `/code-review` 就能触发，参数填完后服务端返回完整 prompt 给 LLM。

> **三分法的设计哲学**：Tools 是动作、Resources 是材料、Prompts 是工作流。**Agent 的三大需求**全覆盖。

---

## 五、客户端反向能力（Roots / Sampling / Elicitation）

MCP 是双向协议——**客户端也能为服务端提供能力**：

| 能力 | 含义 | 用途 |
|---|---|---|
| **Roots** | 客户端告诉服务端它授予访问的"根目录"（filesystem 路径、URL prefix） | server 要知道"允许操作的范围" |
| **Sampling** | server 反过来请求 client 调用 LLM | server 内部需要 LLM 推理时用（避免 server 自己存 API key） |
| **Elicitation** | server 主动请用户补充信息 | "需要您选哪个分支？" |

**这是 MCP 比传统 RPC 多出的一层灵活性**——agent 协作场景常用。

---

## 六、传输层

| 传输 | 适用场景 | 优点 | 缺点 |
|---|---|---|---|
| **stdio** | 本地子进程（最常用） | 零配置、最快、零端口冲突 | 单 client、本地受限 |
| **SSE**（已弃用，仍兼容） | 早期远程方案 | 简单、单向流 | 限制多，已被 Streamable HTTP 取代 |
| **Streamable HTTP** | 远程 server（2026 主推） | HTTP 路由 + 流式响应、可缓存 | 需要鉴权/路由 |
| **WebSocket** | 全双工实时 | 低延迟 | 部署成本高 |

### 6.1 stdio 长什么样

```
Client 进程 fork  ─→  python server.py
                            │ stdin / stdout
   Client ←──── JSON-RPC ───→ Server
   每行一条 JSON 消息（NDJSON）
```

> stdio 之所以受欢迎：**协议序列化用 JSON-RPC，传输直接 stdin/stdout**——零网络、零鉴权问题。Claude Desktop / Claude Code / Cursor 默认就是 stdio。

### 6.2 Streamable HTTP（2026 主流）

```
POST /mcp                ← 单个请求-响应
GET  /mcp                ← SSE 长连接接收 server 推送（双向用）
                         ← 需要 mcp-session-id header 维持会话
```

替换了 2024 年的纯 SSE 方案。实现见 [Cloudflare Workers MCP](https://developers.cloudflare.com/agents/model-context-protocol/) 等。

---

## 七、与 Function Calling 的关系

最常被问的问题。

```
LLM 厂商                  ↓  Function Calling 是这一层（OpenAI/Anthropic/Google 各家协议）
                          │
                          │  json schema → 模型 → tool_use 消息
                          ↓
LLM 应用 (host/client)    ↓  收到 tool_use 后，调用工具
                          │
                          │  调用什么工具？怎么找到工具？怎么连？
                          ↓
工具协议层                ↓  ★ MCP 在这里 ★
                          │
                          │  统一发现、连接、调用工具
                          ↓
工具实现 (server)         ↓  GitHub / DB / FS / ...
```

**两者完全不冲突，是不同层级**：

- 模型怎么"决定调工具"——Function Calling
- 工具怎么"被发现和连接"——MCP

实战中：**MCP server 暴露 tools_list → client 转换为 OpenAI/Anthropic 格式 → 喂给 LLM → LLM 返回 tool_use → client 通过 MCP 调到 server**。

---

## 八、协议的 4 个聪明设计

### 8.1 能力协商（Capability Negotiation）
让协议向后兼容，不会因新功能打挂老 client。

### 8.2 双向 RPC
Server 也能 callback client，支持 Sampling / Elicitation 这类高级模式。

### 8.3 URI-based Resources
用 URI 而不是 ID，**自带命名空间**，跨 server 不冲突。

### 8.4 List + Subscribe 的组合
- `*/list` 一次性拉取
- `notifications/listChanged` 后增量更新
- `resources/subscribe` 单资源订阅

适配从静态到动态变化的 server。

---

## 九、协议版本和演进

```
2024-11 (initial)      首发
2024-11-05             小修
2025-03-26             加入 Streamable HTTP / Elicitation 雏形
2025-06 / 2025-09      增强 Auth / Multi-Modal Resources
2026-03-26 (current)   稳定主版本，OAuth 2.1 集成、Sampling 标准化
```

**版本协商**通过 `protocolVersion` 字段：client 和 server 选**双方都支持的最高版本**。

---

## 十、安全模型概述

MCP 协议本身只规范"怎么传消息"，**不规范"谁能调谁"**——这点经常被忽略。

### 关键安全责任分布
| 责任 | 谁负责 |
|---|---|
| 鉴权（用户身份） | Client + Server 实现层 |
| 授权（哪些用户能用哪些 tool） | Server 实现层（MCP 规范了 OAuth flow） |
| 工具执行隔离（沙箱） | Client + Server 工程实现 |
| Prompt Injection 防护 | Client + 用户 |
| Tool 权限粒度 | Server 设计 |

### 主要威胁面（详见 04 章）
- **Tool Poisoning**：恶意 server 暴露假工具
- **Prompt Injection via Resources**：通过 resource 内容篡改 LLM 行为
- **数据外泄**：滥用工具 + LLM 误判
- **依赖供应链**：npm/pypi 包污染

---

## 十一、读完这章你应该能回答

- MCP 怎么把 M×N 压到 M+N？为什么 Function Calling 不能直接做这件事？
- initialize 协商什么？为什么是双向的？
- Tools / Resources / Prompts 各自适合什么场景？
- stdio / Streamable HTTP / SSE 怎么选？
- Sampling 是干嘛的？为什么 server 反过来要让 client 帮它调 LLM？
- MCP 协议本身管不管鉴权？谁来管？

下一篇：[02-using-mcp.md](02-using-mcp.md) — 怎么用：在 Claude Desktop / Claude Code / Cursor 里挂 server，常用 server 速查与配置示例。
