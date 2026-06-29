# 02. 使用 MCP：在主流客户端里挂载与配置

> 本文从用户/集成方视角讲清楚：**主流 MCP 客户端怎么挂 server、热门 server 速查、典型配置陷阱、调试技巧**。读完你能给自己的 Claude Desktop / Claude Code / Cursor 配上 5-10 个常用 server。

---

## 一、主流 MCP 客户端速查（2026 年中）

| 客户端 | 类型 | 默认协议 | 备注 |
|---|---|---|---|
| **Claude Desktop** | 桌面 chat | stdio | Anthropic 官方，最早支持 |
| **Claude Code** | CLI / IDE | stdio + HTTP | Anthropic 官方编码 Agent |
| **Cursor** | IDE | stdio + HTTP | 配置在 `~/.cursor/mcp.json` |
| **Cline / Roo Code** | VSCode 扩展 | stdio | 工具库丰富 |
| **Continue** | VSCode/JetBrains 扩展 | stdio | 完整 MCP 支持 |
| **Zed** | 编辑器 | stdio | 原生 MCP 集成 |
| **Windsurf** | IDE | stdio + HTTP | Codeium 出品 |
| **Trae** | IDE | stdio + HTTP | 字节系 |
| **VSCode（原生 GitHub Copilot Chat）** | IDE | stdio | 2025 后内置 |
| **LibreChat** | Web UI | HTTP | 开源 chat 前端 |
| **Open WebUI** | Web UI | HTTP | 开源 chat 前端 |

> **配置位置规律**：99% 客户端都把 server 列表放在 `~/.<client>/mcp_config.json` 或 `~/.<client>/claude_desktop_config.json` 这类 JSON 文件，结构基本一致。

---

## 二、Claude Desktop 配置实战

### 2.1 配置文件位置
| 系统 | 路径 |
|---|---|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |
| Linux | `~/.config/Claude/claude_desktop_config.json` |

### 2.2 最小可用配置

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/Users/me/projects"]
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_xxx"
      }
    }
  }
}
```

### 2.3 改完要做什么
1. **完全退出 Claude Desktop**（不是关窗口，是 Quit）
2. 重新打开
3. 看左下角的"🔨 工具"图标——出现 MCP 名称代表已挂上
4. 失败了点图标看错误日志

### 2.4 Stdio 配置三件套

```json
{
  "name-of-server": {
    "command": "..可执行文件..",     // npx / python / node / 自有二进制
    "args":    [...],               // 启动参数
    "env":     {...}                // 环境变量（密钥放这）
  }
}
```

---

## 三、Claude Code 配置（CLI / IDE 通用）

```bash
# 列出当前 MCP servers
claude mcp list

# 加一个 stdio server
claude mcp add filesystem npx -y @modelcontextprotocol/server-filesystem /home/me

# 加一个 HTTP server
claude mcp add my-server --transport http --url https://my-server.example.com/mcp \
  --header "Authorization: Bearer xxx"

# 删除
claude mcp remove filesystem
```

> Claude Code 的 MCP 配置默认存到 `~/.claude.json`。CLI 操作 = 编辑这个文件。

---

## 四、Cursor 配置

### 4.1 配置文件
- 用户级：`~/.cursor/mcp.json`
- 项目级：`<project>/.cursor/mcp.json`（项目内自动加载）

格式与 Claude Desktop 几乎一致：

```json
{
  "mcpServers": {
    "git": {
      "command": "uvx",
      "args": ["mcp-server-git", "--repository", "/path/to/repo"]
    }
  }
}
```

### 4.2 GUI 配置入口
`Cursor Settings → Features → Model Context Protocol`，能可视化加 server。

---

## 五、Cline / Continue 配置

Cline（VSCode 扩展）：
- 通过侧边栏 → MCP Servers → Configure 编辑 JSON
- 文件位置 `~/Library/Application Support/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`

Continue：
- 项目根 `.continue/config.json` 里配 mcpServers

---

## 六、热门 MCP Server 速查（2026 年中）

按用途分类，标了**官方维护**还是**第三方**。

### 6.1 文件 / 系统
| Server | 维护方 | 用途 |
|---|---|---|
| `@modelcontextprotocol/server-filesystem` | 官方 | 读写指定目录 |
| `mcp-server-shell` | 第三方 | 运行 shell 命令（**注意权限**） |
| `mcp-server-git` | 官方 | git 仓库操作 |
| `mcp-server-fetch` | 官方 | URL 抓取 |
| `mcp-server-time` | 官方 | 时区/时间 |

### 6.2 数据库
| Server | 维护方 | 用途 |
|---|---|---|
| `mcp-server-postgres` | 官方 | PostgreSQL（只读默认） |
| `mcp-server-sqlite` | 官方 | SQLite |
| `mcp-server-mongodb` | 第三方 | MongoDB |
| `mcp-server-mysql` | 第三方 | MySQL |
| `mcp-server-redis` | 第三方 | Redis |
| `mcp-server-clickhouse` | 第三方 | ClickHouse |

### 6.3 代码托管 / DevOps
| Server | 维护方 | 用途 |
|---|---|---|
| `@modelcontextprotocol/server-github` | 官方 | GitHub PR/Issue/repo |
| `mcp-server-gitlab` | 第三方 | GitLab |
| `mcp-server-bitbucket` | 第三方 | Bitbucket |
| `mcp-server-jenkins` | 第三方 | Jenkins |
| `mcp-server-aws-cdk` / `aws-mcp-suite` | 第三方 | AWS 操作 |
| `mcp-server-kubernetes` | 第三方 | k8s 集群 |

### 6.4 团队协作 / IM
| Server | 维护方 | 用途 |
|---|---|---|
| `mcp-server-slack` | 官方 | Slack |
| `mcp-server-discord` | 第三方 | Discord |
| `mcp-server-teams` | 第三方 | MS Teams |
| `mcp-server-gmail` | 官方 | Gmail |
| `mcp-server-feishu` / `mcp-lark` | 第三方 | 飞书 |

### 6.5 Web 自动化
| Server | 维护方 | 用途 |
|---|---|---|
| `@modelcontextprotocol/server-puppeteer` | 官方（已退役） | 浏览器自动化 |
| `mcp-server-playwright` | 官方/第三方 | Playwright 浏览器 |
| `mcp-server-browserbase` | Browserbase | 远程浏览器 |
| `mcp-server-firecrawl` | Firecrawl | 网站抓取 |

### 6.6 设计 / 文档
| Server | 维护方 | 用途 |
|---|---|---|
| `mcp-server-figma` | Figma | Figma 文件读取 |
| `mcp-server-notion` | 第三方 | Notion |
| `mcp-server-confluence` | Atlassian | Confluence |
| `mcp-server-jira` | Atlassian | Jira |

### 6.7 AI / 数据
| Server | 维护方 | 用途 |
|---|---|---|
| `mcp-server-pinecone` | Pinecone | Pinecone 向量库 |
| `mcp-server-qdrant` | Qdrant | Qdrant 向量库 |
| `mcp-server-weaviate` | Weaviate | Weaviate |
| `mcp-server-snowflake` | 第三方 | 数仓 |
| `mcp-server-bigquery` | 第三方 | BigQuery |

### 6.8 实用小工具
| Server | 用途 |
|---|---|
| `mcp-server-time` | 时区计算（写代码常需要） |
| `mcp-server-memory` | LLM 工作记忆持久化 |
| `mcp-server-everything` | demo 用 server，含 sample 工具 |
| `mcp-server-sequential-thinking` | 让 LLM 走显式 step-by-step 思考 |

> **完整目录**：[github.com/modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers) + [github.com/punkpeye/awesome-mcp-servers](https://github.com/punkpeye/awesome-mcp-servers) + [pulsemcp.com](https://pulsemcp.com)

---

## 七、典型配置陷阱

### 7.1 路径陷阱
```json
"args": ["-y", "@modelcontextprotocol/server-filesystem", "~/projects"]
```
**`~` 不会被展开**！换成绝对路径：

```json
"args": ["-y", "@modelcontextprotocol/server-filesystem", "/Users/me/projects"]
```

### 7.2 npx 第一次会下载
首次启动可能慢 30-60 秒。卡住别急，去掉 `-y` 看 stderr 提示。

### 7.3 npx vs 全局安装
- 用 `npx -y xxx`：每次启动都查更新（稳定但慢）
- 全局 `npm install -g xxx` 然后 `command: "xxx"`：快但不更新

### 7.4 多个项目共享 server
项目级配置（如 Cursor 的 `.cursor/mcp.json`）会**继承用户级**，重名 server 项目级覆盖用户级。

### 7.5 环境变量泄密
```json
"env": { "GITHUB_TOKEN": "ghp_xxx" }
```
配置文件**不能进 git**。把它加到 `.gitignore`，或用 `${env:GITHUB_TOKEN}` 占位（取决于客户端是否支持）。

### 7.6 Windows 的 npx 坑
Windows 下命令要写 `npx.cmd` 而不是 `npx`：

```json
"command": "npx.cmd",
```

或用 cross-env / `cmd /c`。

---

## 八、调试 5 招

### 8.1 看 client 日志
- Claude Desktop: `~/Library/Logs/Claude/mcp*.log`（macOS）
- Claude Code: `claude` 命令带 `--debug`
- Cursor: 输出面板选 "MCP"

### 8.2 用 MCP Inspector
官方 GUI 调试工具：

```bash
npx @modelcontextprotocol/inspector node my-server.js
```
打开浏览器，能直接看 server 暴露的 tools/resources/prompts，手动调用。**自己写 server 必装**。

### 8.3 stdio 直接 echo
单步调试 stdio server：

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2026-03-26","capabilities":{}}}' | python my_server.py
```
看输出的 JSON-RPC 响应。

### 8.4 server 端打 log 到 stderr
**不能打到 stdout**——stdout 是协议通道，会污染消息流。

```python
import sys
print("debug info", file=sys.stderr)
```

### 8.5 包装代理工具
[`@modelcontextprotocol/server-everything`](https://github.com/modelcontextprotocol/servers/tree/main/src/everything) demo server 涵盖所有协议功能，对照学习最直观。

---

## 九、什么时候应该挂 MCP，什么时候不该挂

### ✅ 适合挂的
- 重复性强的工具调用（git、shell、DB 查询）
- 跨多个 LLM 应用复用（家里、公司、CI 都要用）
- 数据 / 文件源需要"挂载"（codebase、docs）
- 已有成熟 server 的（如 GitHub、Notion）

### ❌ 不适合挂的
- 仅一次性使用的工具（直接 prompt 里贴数据更快）
- 极端低延迟需求（MCP 多一层 IPC 开销）
- 涉及高敏感操作但 server 鉴权不充分（先做安全审计）
- 内网无法部署 server runtime 的环境

---

## 十、企业内部署常见模式

### 10.1 小团队（5-20 人）
- 共享 GitHub repo 维护一份 `mcp-config-shared.json`
- 配合 `.env.example` + 1Password / Vault 管密钥

### 10.2 中型团队（50-500 人）
- 自建 **MCP Gateway**：统一鉴权 + 多 tenant + 限流（详见 03 章）
- 公司内 server 走 HTTP，外部公开 server 还是 stdio

### 10.3 大型企业
- 走 **MCP-as-a-Service**：内部平台部署 server 集群
- IAM 集成（SAML / OIDC）
- 审计日志 + 合规审查

> 详见 [04-industry-landscape.md](04-industry-landscape.md) §企业级方案。

---

## 十一、给开发者的 5 条经验

1. **从 filesystem + git + fetch 起步**——这三个 server 解决 80% 日常需求。
2. **每加一个 server 都验证一次**——挂多了往往会有 server 启动崩，要逐个看。
3. **密钥用环境变量，永远不进 git**。
4. **MCP Inspector 不是可选**——自己写 server 时这是唯一可靠的调试工具。
5. **"server 多 ≠ Agent 强"**——LLM 看到的工具列表过长会选不准。一个客户端 10-20 个 server 是合理上限。

---

下一篇：[03-developing-mcp-servers.md](03-developing-mcp-servers.md) — 自己写一个 MCP server：Python/TypeScript SDK、tool/resource/prompt 设计、鉴权、生产部署。
