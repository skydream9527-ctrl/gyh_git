# MCP 深度专题：原理 / 使用 / 开发 / 业界方案

> **MCP（Model Context Protocol）** 是 Anthropic 在 2024 年 11 月推出的开源协议，目标是统一 LLM 应用与外部数据/工具的连接方式——一句话："**AI 应用的 USB-C**"。
>
> 一年多过去，它已是事实工具协议：Claude Desktop / Claude Code / Cursor / Cline / Continue / Zed / Windsurf 全部原生支持，社区 server 数千个。本目录系统讲清楚 MCP 的**协议原理、客户端使用、服务端开发、业界最佳实践**。

---

## 阅读顺序

| 顺序 | 文件 | 解决什么问题 |
|---|---|---|
| 1 | [01-mcp-principles.md](01-mcp-principles.md) | 为什么是 MCP / 协议本身怎么设计的（JSON-RPC, lifecycle, capabilities, transport） |
| 2 | [02-using-mcp.md](02-using-mcp.md) | 用户/开发者侧：在 Claude Desktop / Claude Code / Cursor 里怎么挂 server，常用 server 速查 |
| 3 | [03-developing-mcp-servers.md](03-developing-mcp-servers.md) | 自己写一个 MCP server：Python/TypeScript SDK、tool/resource/prompt 设计、鉴权、调试 |
| 4 | [04-industry-landscape.md](04-industry-landscape.md) | 业界生态：官方/社区 server 全景、企业级方案、安全治理、与 Function Calling/Plugin 的边界 |

---

## 关键问题清单（读完应能回答）

- 为什么 OpenAI Function Calling 不够，必须搞 MCP？
- MCP 协议消息长什么样？lifecycle 怎么走？
- Tools / Resources / Prompts 三类能力的边界是什么？
- stdio / SSE / Streamable HTTP / WebSocket 各自什么时候用？
- 怎么用 Python `FastMCP` 在 50 行代码里写一个 server？
- TypeScript SDK 怎么写、怎么打包成 npm 包？
- 怎么给 server 加鉴权 / 限流 / 多租户？
- MCP 在生产里典型的安全坑是什么（prompt injection / tool poisoning / 资源泄露）？
- 业界企业级方案：Cloudflare、Pulumi、Glama、PulseMCP、Smithery 在做什么？

---

## 与本仓库其它资料的关系

| 资料 | 关系 |
|---|---|
| [../tools-protocols/mcp.md](../tools-protocols/mcp.md) | 入门版速查（架构图、最小 server 示例）。本目录是它的深入篇。 |
| [../tools-protocols/function-calling.md](../tools-protocols/function-calling.md) | Function Calling 基础。本目录 01 章会对比两者关系。 |
| [../tools-protocols/tool-development.md](../tools-protocols/tool-development.md) | API 工程师视角的工具设计。03 章会引用 schema 设计要点。 |

---

## 一句话定位

```
   Function Calling   = LLM ↔ 工具的"通话语法"     (单家厂商内的事)
                          ↓
       MCP            = 跨 LLM 应用与跨工具的"通用接线"  (M+N 而非 M×N)
                          ↓
        生产 Agent      = LLM 模型 + Function Calling + MCP + 沙箱 + 鉴权
```

---

## 关键参考

- [modelcontextprotocol.io](https://modelcontextprotocol.io/) — 官方文档
- [github.com/modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers) — 官方 server 集合
- [github.com/punkpeye/awesome-mcp-servers](https://github.com/punkpeye/awesome-mcp-servers) — 社区 awesome 清单
- Anthropic — *Introducing the Model Context Protocol*（2024.11）
- *Building Agents with Model Context Protocol* — Anthropic Skill Tutorial
- Cloudflare — *Workers as MCP servers*（2025）
- *MCP Specification 2026-03-26* — 最新协议版本
