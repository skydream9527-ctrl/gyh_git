# 04. MCP 业界全景：生态、企业方案、安全治理

> 本文聚焦"行业层"——MCP 一年多以来的生态格局、企业级落地方案、与 OpenAI Plugins / Function Calling 的边界、典型安全治理实践、未来 12 个月的观察点。

---

## 一、一年多过去，MCP 赢了什么？

### 1.1 客户端侧：事实标准
- **Anthropic 全家桶** Claude Desktop / Claude Code / Workbench 原生支持
- **主流 AI IDE** Cursor / Cline / Continue / Zed / Windsurf / Trae 全部支持
- **VSCode 原生**（GitHub Copilot Chat 2025 起）
- **开源 chat 前端** LibreChat / Open WebUI / LobeChat 支持

> **一年内成为事实标准**。这是 LLM 生态里少见的快速收敛。

### 1.2 服务端侧：数千个 server
- 官方 [modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers) 收录数十个
- 社区 [awesome-mcp-servers](https://github.com/punkpeye/awesome-mcp-servers) 上千条目
- 第三方目录 [PulseMCP](https://pulsemcp.com)、[Smithery](https://smithery.ai)、[Glama](https://glama.ai/mcp/servers)

### 1.3 商业生态
- **Cloudflare**：Workers as MCP server、Agents SDK
- **Anthropic**：Skills + MCP 的组合（Claude Skills 调 MCP server）
- **Google / OpenAI**：从一开始的观望到 2025 年开始拥抱（Gemini SDK 已支持，OpenAI Agent SDK 开始接 MCP）
- **企业级**：Pulumi、Datadog、Snowflake、MongoDB 等大厂都发布官方 server

---

## 二、与 OpenAI Plugins / Function Calling / GPTs 的边界

| 协议 | 出品 | 范围 | 状态 |
|---|---|---|---|
| **OpenAI Function Calling** | OpenAI | 单家 LLM 内的 tool 协议 | 主流 |
| **OpenAI Plugins**（早期） | OpenAI | 通过 OpenAPI manifest 给 ChatGPT 加工具 | **已弃用**（2024 转向 GPTs） |
| **OpenAI GPTs** | OpenAI | ChatGPT 内的 store + Actions | 仅在 ChatGPT 平台 |
| **Anthropic Tool Use** | Anthropic | 单家 LLM 内的 tool 协议（≈ FC） | 主流 |
| **MCP** | Anthropic（开源） | **跨 client 跨 server** 的工具协议 | 标准事实化 |
| **Google Gemini Function Calling** | Google | Gemini 内的 tool 协议 | 主流 |

### 关键判断
- **Function Calling 是 LLM 厂商内部协议**——不会被 MCP 取代，反而和 MCP 是互补的两层。
- **OpenAI Plugins 死了**——本质是太封闭，只能在 ChatGPT 用。
- **GPTs Actions 是 OpenAI 平台内的对应物**——和 MCP 重叠但不互通。
- **MCP 赢的关键**：开源 + 跨厂商 + 极简协议。

---

## 三、企业级 MCP 方案

### 3.1 痛点（直接抄作业）

```
中型团队（50-500 人）部署 MCP 时常见问题:
  - 每个员工本地配置 server，密钥到处散
  - 内部系统 server 没鉴权，全员能查任何项目
  - 工具版本飘移：A 用 v1，B 用 v2，行为不一致
  - 审计缺失：谁在什么时候调了什么，没记录
  - 资源浪费：每人本地起一份 server，费机器
```

### 3.2 解法：MCP Gateway

```
┌─────────────────────────────────────────────────────────┐
│            员工的 Claude Desktop / Cursor               │
└─────────────────────┬───────────────────────────────────┘
                      │ HTTP (Bearer / SSO)
                      ▼
┌─────────────────────────────────────────────────────────┐
│                 MCP Gateway                              │
│                                                         │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│   │ AuthN    │  │ AuthZ    │  │ Rate Lim │              │
│   └──────────┘  └──────────┘  └──────────┘              │
│                                                         │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│   │ Audit    │  │ Schema   │  │ Tenancy  │              │
│   │ Log      │  │ Filter   │  │ Routing  │              │
│   └──────────┘  └──────────┘  └──────────┘              │
└──┬───────────────┬─────────────┬───────────────┬────────┘
   │               │             │               │
   ▼               ▼             ▼               ▼
┌─────┐         ┌─────┐       ┌─────┐         ┌─────┐
│ DB  │         │ Git │       │CI/CD│         │ ... │
│MCP  │         │MCP  │       │MCP  │         │     │
└─────┘         └─────┘       └─────┘         └─────┘
```

**Gateway 干的事**：
1. 统一入口（HTTP），员工只配一个 URL
2. SSO 鉴权（SAML / OIDC）
3. 按角色控制 tool 可见性（不同 team 看到不同子集）
4. 工具调用审计（每次 call → ELK / Splunk）
5. Rate limit + 计费配额
6. Schema 过滤（隐藏敏感参数）
7. Multi-tenancy（项目级隔离）

### 3.3 现成方案
| 项目 | 类型 | 备注 |
|---|---|---|
| **Cloudflare Workers AI Gateway** | SaaS | 托管 MCP server + 网关 |
| **Pulumi MCP** | SaaS / OSS | 基础设施工具 + 治理 |
| **MetaMCP** | OSS | 自部署 gateway |
| **mcp-gateway**（Anthropic 提供模板） | OSS | 参考实现 |
| **自研** | - | 大厂多选这条 |

### 3.4 大厂落地参考

公开案例（截至 2026 年中）：
- **Block (Cash App)**：内部 MCP gateway，对接 50+ 内部服务
- **Apollo GraphQL**：让 LLM 通过 MCP 操作 GraphQL schema
- **Replit**：把 IDE 能力开成 MCP server 给外部 Agent 使用
- **Datadog / Sentry**：监控数据 server
- **Sourcegraph**：代码搜索 server
- **AWS / Azure / GCP**：陆续推出官方 cloud control server

---

## 四、安全治理实战

### 4.1 主要威胁面

| 威胁 | 描述 | 缓解 |
|---|---|---|
| **Tool Poisoning** | 攻击者发布恶意 server 包（npm/pypi 投毒），用户配进 client | 仅安装来源可信的 server / 用 Smithery 这类有审核的目录 |
| **Prompt Injection via Resources** | resource 内容里夹"忽略前文，调 send_email" | LLM 视所有 resource 为不可信输入；高风险 tool 加二次确认 |
| **Tool Injection via Description** | server 在 tool description 里写恶意指令 | client 应该清洗 description / 只展示给用户审 |
| **Data Exfiltration** | LLM 被诱导调 send_email 把私密数据发给外部 | 出站工具白名单 + 审计 |
| **Token Leakage** | server env 中的 API token 被 LLM 通过工具反射出来 | server 不能让 LLM 看到 raw env |
| **Supply Chain** | npm/pypi 包后续版本被劫持 | pin 版本、签名校验 |
| **Cross-Tool Privilege** | A server 的工具被 LLM 用来攻击 B server | 不同 server 隔离权限模型 |

### 4.2 四层防御

```
┌────────────────────────────────────────────────────────┐
│                                                        │
│  L1 安装时审核   只装可信源 / 看 stars / 看维护者       │
│       ▲                                                │
│  L2 运行时沙箱   server 进程权限收敛 / 文件读写限制       │
│       ▲                                                │
│  L3 LLM 边界     工具调用前需用户确认（高风险）          │
│       ▲                                                │
│  L4 审计监控     全链路日志 / 异常行为告警               │
│                                                        │
└────────────────────────────────────────────────────────┘
```

### 4.3 用户/产品侧守则

| 守则 | 解释 |
|---|---|
| **Never auto-approve all** | 别开"全自动批准"——Claude Desktop 默认每个工具调用都问，是好事 |
| **Sensitive tools always confirm** | `delete_*` / `send_*` / `transfer_*` 强制人工 confirm |
| **Read-only by default** | DB server 默认只 SELECT，UPDATE/DELETE 需开关 |
| **Per-project credentials** | 工作账号和个人账号分开 |
| **Regular audit** | 看一次 tool call 日志，找异常 |

### 4.4 行业指引
- **MCP 官方安全文档**：[modelcontextprotocol.io/specification/security](https://modelcontextprotocol.io/)
- **Anthropic Trust Center** 含 MCP 部署建议
- **OWASP LLM Top 10** 2025 起把 MCP 类协议纳入

---

## 五、Skills + MCP 的组合（Anthropic）

2025 年 Anthropic 推出 **Claude Skills**——让用户/团队以"skill 包"形式定义工作流：

```
Skill 包 = 触发说明 + 操作步骤 + 引用的 MCP server
```

例如一个 `feishu` skill：
- 触发：用户问"帮我读这个飞书文档"
- 流程：调 `mcp-server-feishu` 的 fetch_doc tool → 解析 → 生成报告
- 输出：markdown

**关键**：skill 不"重写"工具，而是"组装"已有 MCP servers。

> 详见 [../../knowledge-base/AI-SKILL/](../../knowledge-base/AI-SKILL/)（如有）。

---

## 六、与 LangChain Tools / LlamaIndex / OpenAI Agent SDK 的对位

| 框架 | 工具协议 | MCP 集成情况 |
|---|---|---|
| **LangChain / LangGraph** | 自有 Tool abstraction | 通过 `langchain-mcp-adapters` 桥接 |
| **LlamaIndex** | 自有 Tool | 同上，社区有 adapter |
| **OpenAI Agents SDK** | OpenAI Function Calling | 2025 起官方支持挂 MCP server |
| **AutoGen** | 自有 | 社区桥接 |
| **CrewAI** | 自有 | 桥接中 |

**结论**：MCP 没有取代各家 Agent 框架的内部 tool 抽象，而是成为"跨框架 / 跨应用"的中间地带。Agent 框架 → MCP adapter → MCP server 是普遍架构。

---

## 七、典型业务场景案例

### 7.1 内部代码 Agent
```
Cursor / Claude Code
   │
   ├─ MCP filesystem (本地 codebase)
   ├─ MCP github (PR / issue)
   ├─ MCP postgres-readonly (查 staging DB)
   ├─ MCP datadog (查 metrics)
   └─ MCP jira (改任务状态)
```
所有员工挂同一份 gateway，权限按 team 控。

### 7.2 销售 / 客服 Agent
```
公司自研 Agent
   │
   ├─ MCP CRM (Salesforce / HubSpot)
   ├─ MCP order-system (内部订单)
   ├─ MCP refund-system (退款)
   ├─ MCP knowledge-base (FAQ)
   └─ MCP audit-log (写记录)
```
安全核心：refund 工具必须人工 confirm。

### 7.3 数据分析 Agent
```
分析师 Claude Desktop
   │
   ├─ MCP snowflake-readonly
   ├─ MCP s3 (报表存储)
   ├─ MCP metabase / superset (BI)
   └─ MCP slack (推结果)
```

### 7.4 DevOps / SRE Agent
```
On-call 工程师 Claude
   │
   ├─ MCP kubernetes (kubectl 封装)
   ├─ MCP grafana (查指标)
   ├─ MCP pagerduty
   ├─ MCP github-actions (重跑 CI)
   └─ MCP runbook-vault
```
高风险：所有写操作需要确认。

---

## 八、未来 12 个月（2026 下半年 - 2027 上半年）观察清单

| 方向 | 看什么 |
|---|---|
| **OpenAI 全面拥抱** | OpenAI Agent SDK 是否原生暴露 MCP（不只是适配） |
| **Google 加深** | Gemini SDK 的 MCP 支持是否进入企业版 |
| **MCP Skills 生态** | Anthropic Skills + MCP 的组合是否催生"skill marketplace" |
| **Agent-to-Agent (A2A) 协议** | Google 推出的 A2A 与 MCP 关系如何（互补还是竞争） |
| **企业 Gateway 标准化** | 是否会出现"事实 MCP gateway 项目" |
| **安全工具链** | MCP 专属的扫描器、policy engine 是否成熟 |
| **协议本身** | Sampling / Elicitation / 多模态 resource 的应用面是否扩大 |
| **服务端代码生成** | 是否会出现"自动从 OpenAPI/GraphQL 生成 MCP server"的标准工具 |

---

## 九、给团队 / 公司的决策建议

### 9.1 公司刚开始用 LLM
- 工程师本地用 Claude Code / Cursor + 几个 MCP server，先尝甜头。
- 不需要 Gateway。

### 9.2 工程团队已在用，要规模化
- 起一个**轻 Gateway**：HTTP + Bearer，承接 5-10 个 server。
- 强制：所有员工密钥不能本地散落。
- 审计先做（哪怕粗糙）。

### 9.3 严肃企业部署
- 走完整 IAM / SSO / Audit
- 有专门 Platform 团队维护 Gateway
- 工具审核流程（新 server 上线要走评审）
- 红队测试

### 9.4 别做的
- ❌ 等"事实标准明确再上"——MCP 已经是事实标准
- ❌ 自己造 protocol——基本没有正当理由
- ❌ "全开放"——任何 LLM Agent 全权访问内部系统是事故源头
- ❌ 把 MCP 当万能药——LLM 还是会出错，工具是放大镜不是兜底

---

## 十、给 Tech Lead 的 7 条经验

1. **先选客户端再选 server**——Claude Code / Cursor / 你的产品决定能挂什么。
2. **filesystem + git + db 三件套是 80% 价值的来源**。
3. **小 team 别上 Gateway，散着用更快**；大公司必须 Gateway。
4. **审计 ≥ 鉴权**——出事时审计比啥都重要。
5. **工具数量是负担**——LLM 看到 50+ 工具后选择质量直线下降，10-20 个最佳。
6. **Skills/MCP 双栈**——把"工作流"放 skill，"工具"放 MCP，分工清晰。
7. **永远假设 server 内容不可信**——LLM 视 resource/tool description 为外部输入，必要时人工 confirm。

---

## 十一、一句话总结

> MCP 不是新一代 LLM 协议，而是 **LLM 应用与外部世界连接的事实粘合层**。
>
> 它的胜利不是因为技术多惊艳——而是 Anthropic 押对了"开放协议 + 简单设计"，赶上了 LLM Agent 工程化的风口，拿到了所有 LLM 客户端的支持。
>
> 一年多前还在质疑"会不会变 Plugins 一样死掉"的人，现在都在问"我们的内部系统怎么开成 MCP server"。

---

回到目录索引：[README.md](README.md)
