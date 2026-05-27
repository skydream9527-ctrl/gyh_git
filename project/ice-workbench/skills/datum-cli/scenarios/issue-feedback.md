# 问题反馈（提交 GitLab Issue）

> 当使用 datum CLI 遇到无法解决的问题时，通过此流程向维护者提交反馈。

## 触发条件

**AI 主动提议：**
- 经过完整排查路径（`--dry-run` → `-v` → OpenAPI 文档）仍无法解决
- 命令行为与文档描述明显不一致，疑似 CLI 本身 bug
- API 返回无法解释的异常错误

**用户主动触发：**
- 用户表达"帮我反馈这个问题"、"提个 issue"等类似意图

## 反馈流程

```
1. 收集信息 → 2. 组装 Issue → 3. 脱敏检查 → 4. 用户确认 → 5. 获取 Token → 6. 提交 Issue → 7. 记录结果
```

### 第一步：收集信息

自动收集以下内容：

```bash
# 环境信息
datum version                          # CLI 版本
uname -s && uname -m                   # OS / Arch（macOS/Linux）
```

从当前会话上下文中提取：
- **使用的命令**：导致问题的完整 datum 命令
- **错误输出**：关键错误信息（截取核心部分）
- **已尝试的排查步骤**：按顺序罗列已做过的排查

同时询问用户姓名，**建议用户填写小米公司邮箱前缀**（如 `zhangsan`），方便维护者反馈处理结论。非必填，用户可选择匿名。

### 第二步：组装 Issue 内容

按以下模板组装，**总字符数不超过 3000 字符**：

```markdown
## 环境信息

- datum 版本: <datum version 输出>
- OS / Arch: <操作系统和架构>
- AI 工具: <当前使用的 AI 工具名称，如 OpenCode / Claude Code / Cursor 等>
- 反馈人: <用户提供的邮箱前缀（如 zhangsan），未提供则写"匿名用户">

## 问题描述

**期望行为：** <一句话描述期望结果>

**实际行为：** <一句话描述实际结果>

## 复现步骤

1. <最小化复现步骤>
2. ...

## 已尝试的排查

1. <排查步骤及结果，每步不超过 2 行>
2. ...

## 关键错误输出

```
<截取关键部分，不超过 50 行>
```

## 补充信息

<如有其他相关上下文>
```

### 第三步：脱敏检查

提交前 **必须** 检查并移除以下敏感信息：
- Token、密码、API Key（替换为 `<REDACTED>`）
- 内部 IP 地址、域名（非公开的）
- 个人身份信息（邮箱、工号等）
- 业务数据内容（表数据、SQL 中的具体业务值）

### 第四步：用户确认

将组装好的 Issue 标题和内容展示给用户，**必须** 获得用户明确确认后才能提交：

> 我整理了以下反馈 Issue，请确认内容是否准确，确认后我将提交到 GitLab：
>
> **标题：** [datum-cli] xxx
> **内容：** （展示完整内容）
>
> 确认提交吗？

### 第五步：获取 Token

每次提交前从远程获取最新 Token，确保不会因本地 Token 过期而失败。

**获取方式：** 通过 HTTP 请求拉取远程 Token 文件：

| 参数 | 值 |
|------|-----|
| 方法 | `GET` |
| URL | `https://cnbj1-fds.api.xiaomi.net/datum-cli/FEEDBACK_GITLAB_TOKEN` |

响应体为纯文本，即 Token 字符串（去除首尾空白后使用）。

**失败处理：** 如果无法获取远程 Token（网络不通、404 等），直接跳转到手动回退方式。

### 第六步：提交 Issue

通过 HTTP 请求调用 GitLab API 创建 Issue。AI 根据当前运行环境自行选择发起 HTTP 请求的方式（如 curl、PowerShell、Python 等），无需限定具体工具。

**请求参数：**

| 参数 | 值 |
|------|-----|
| 方法 | `POST` |
| URL | `https://git.n.xiaomi.com/api/v4/projects/zebinbin%2Fdatum_cli/issues` |
| Header | `PRIVATE-TOKEN: <从第五步获取的 Token>` |
| Header | `Content-Type: application/json` |
| Body 字段 | `title`: Issue 标题，以 `[datum-cli]` 开头 |
| Body 字段 | `description`: 第二步组装的 Issue 内容 |
| Body 字段 | `labels`: `ai-agent-feedback` |

**成功响应（HTTP 201）：** 返回 JSON，包含 `web_url` 字段即为 Issue 链接。

**失败处理（HTTP 401 或其他错误）：** 回退到手动提交方式（见下方）。

**手动回退：**

如果 HTTP 请求无法发起（极端环境限制）或续期失败，提供以下信息让用户手动提交：

```
自动提交失败，请手动创建 Issue：

1. 打开: https://git.n.xiaomi.com/zebinbin/datum_cli/-/issues/new?issue[title]=<URL 编码的标题>&issue[description]=<URL 编码的描述>
2. 检查预填充的标题和描述是否正确
3. 手动添加 Label: ai-agent-feedback
4. 点击提交
```

> 注意：GitLab 预填充 URL 支持 `issue[title]` 和 `issue[description]` 参数，但 **不支持** 预填充 Labels，需要用户手动添加。

### 第七步：记录结果

- 提交成功后，向用户展示 Issue 链接
- 同一会话内记住已提交的 Issue URL，避免重复提交同一问题

## 内容控制规则

| 区域 | 限制 |
|------|------|
| Issue 标题 | 不超过 80 字符 |
| 错误输出 | 截取关键部分，不超过 50 行 |
| 排查步骤 | 每步不超过 2 行，最多 10 步 |
| Issue 总体 | 不超过 3000 字符 |

超出限制时，优先保留：错误信息 > 复现步骤 > 排查历史 > 环境信息。

## 注意事项

- **先确认再提交**：永远不要未经用户确认就创建 Issue
- **脱敏优先**：宁可丢失部分上下文，也不能泄露敏感信息
- **不重复提交**：同一会话内同一问题只提交一次
- **标题规范**：统一以 `[datum-cli]` 前缀开头，便于筛选
- **Label 固定**：始终使用 `ai-agent-feedback` label
- **Token 安全**：Token 仅用于创建 Issue，不要在 Issue 内容或日志中输出 Token 值
