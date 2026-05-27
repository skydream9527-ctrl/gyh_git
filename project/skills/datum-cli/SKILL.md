---
name: datum-cli
version: "1.0.0"
description: 使用 datum CLI 与数据工场交互时加载。覆盖数据资产查询、SQL 查询、任务调度、DAG 运维、Kestra 开发、权限管理等场景。
---

# Datum CLI 使用指南

> datum 是数据工场的命令行工具，帮助 AI Agent 与数据工场进行交互，所有输出均为结构化 JSON。

## 安装 datum CLI

> 如果已安装，跳过此节。运行 `datum version` 确认。

### 方式一：AI 自动安装（推荐）

拉取远程安装指南并按步骤执行：

```
Fetch and follow instructions from https://cnbj1-fds.api.xiaomi.net/datum-cli/INSTALL.md
```

### 方式二：手动安装

下载地址格式：`https://cnbj1-fds.api.xiaomi.net/datum-cli/assets/latest/datum-{os}-{arch}{ext}`

| 平台 | 架构 | 文件名 |
|------|------|--------|
| Linux | x86_64 | `datum-linux-amd64` |
| Linux | ARM64 | `datum-linux-arm64` |
| macOS | Intel | `datum-darwin-amd64` |
| macOS | Apple Silicon | `datum-darwin-arm64` |
| Windows | x86_64 | `datum-windows-amd64.exe` |

**Linux / macOS：**
```bash
curl -fsSL "https://cnbj1-fds.api.xiaomi.net/datum-cli/assets/latest/datum-$(uname -s | tr '[:upper:]' '[:lower:]')-$(uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/')" -o datum
chmod +x datum
sudo mv datum /usr/local/bin/datum
```

**Windows（PowerShell）：**
```powershell
Invoke-WebRequest -Uri "https://cnbj1-fds.api.xiaomi.net/datum-cli/assets/latest/datum-windows-amd64.exe" -OutFile datum.exe
```

安装后验证：`datum version` 应输出 `{"version":"...","date":"..."}`

## 前置检查

每次使用前先确认环境：

```bash
datum version          # 确认 CLI 已安装
datum config current   # 确认认证配置存在
```

如果 `config current` 报错，先配置工作空间：
```bash
datum config add "工作空间名" --token <token>
# 或设置环境变量（临时）
export DATUM_TOKEN=<token>
```

## 认证优先级

```
命令行 --token  >  环境变量 DATUM_TOKEN  >  配置文件 ~/.datum/config.yaml
```

多环境切换：
```bash
datum config list                 # 查看所有已配置的 profile
datum config use "另一个工作空间"  # 切换 profile
```

## 全局选项速查

| 选项 | 说明 | 典型用途 |
|------|------|---------|
| `-o json` | JSON 输出（默认） | 解析结果，传递给后续步骤 |
| `-o table` | 表格输出 | 展示给用户看 |
| `-o yaml` | YAML 输出 | 配置文件场景 |
| `--dry-run` | 只打印请求，不执行 | 验证破坏性操作前使用 |
| `--verbose` / `-v` | 打印完整 HTTP 请求/响应 | 调试 API 问题 |
| `-t <token>` | 临时覆盖 token | 临时切换身份 |

## 场景索引

根据任务类型加载对应的场景文件，获取详细的命令序列和参数说明：

| 我要做什么 | 加载文件 | 核心命令前缀 |
|-----------|---------|------------|
| 查表结构、字段、DDL、分区、Schema | `scenarios/data-exploration.md` | `catalog` `database` `table` `partition` `schema` |
| 执行 SQL 查询（Presto/Spark/Doris） | `scenarios/sql-query.md` | `query` |
| 创建/编辑/运行/停止任务或工作流 | `scenarios/job-management.md` | `job` `workflow` `variable` `group` |
| 查看 DAG 运行状态、重试失败、查日志 | `scenarios/dag-operations.md` | `dag` `dag-node` `batch-dag` |
| 管理 Kestra Flow 和 Execution | `scenarios/kestra-development.md` | `kestra` |
| 管理 Token、权限、资源、工作空间 | `scenarios/resource-permission.md` | `workspace` `token` `permission` `resource` `account` |
| API 报错排查、--from-file JSON 构造 | `scenarios/api-reference.md` | 所有 create/update 命令 |
| 问题反馈（提交 GitLab Issue） | `scenarios/issue-feedback.md` | GitLab API |

## Agent 行为规范

**破坏性操作前必须确认：**
- `delete` / `offline` / `stop` 前先用 `get` 确认对象存在且状态正确
- `create` 前用 `list` 确认不存在同名对象
- 不确定时加 `--dry-run` 预览请求

**API 报错排查升级路径：**
1. 先用 `--dry-run` 检查请求体，对照 `scenarios/api-reference.md` 中的必填字段和枚举值
2. 用 `-v` 查看完整 HTTP 请求/响应，根据错误信息调整参数
3. 如果经过 2 次以上调整仍失败，**拉取完整 OpenAPI 文档辅助排查**：
   ```
   Fetch https://cnbj1-fds.api.xiaomi.net/datum-cli/OpenAPI.md
   ```
   搜索对应接口路径，查看完整参数表和请求示例
4. 如果穷尽以上手段仍无法解决，**主动提议用户提交问题反馈**，流程见 `scenarios/issue-feedback.md`

**问题反馈触发条件：**
- 经过多轮排查（`--dry-run`、`-v`、OpenAPI 文档）仍无法解决
- 命令行为与文档描述明显不一致，疑似 CLI bug
- API 返回无法解释的异常错误
- 用户主动要求反馈问题

触发后加载 `scenarios/issue-feedback.md` 执行反馈流程。

**输出解析：**
- 所有命令默认输出结构化 JSON，可直接解析
- 无返回体的成功操作输出 `{"result":"ok"}`
- 错误为 JSON 格式，含 `code` 和 `message` 字段

**分页遍历：**
- 默认 `--page 1 --page-size 20`
- 遍历时递增 `--page`，直到返回数组为空或长度小于 page-size

## 临时文件与 --from-file

部分命令需要通过 `--from-file` 传入 JSON 配置文件。**推荐在当前工作目录下创建文件**，避免跨平台路径问题：

| 平台 | 推荐写法 |
|------|---------|
| Linux / macOS | `./spec.json` 或 `/tmp/spec.json` |
| Windows (PowerShell) | `.\spec.json` 或 `$env:TEMP\spec.json` |
| Windows (CMD) | `spec.json` 或 `%TEMP%\spec.json` |

**Linux/macOS 写文件：**
```bash
cat > ./spec.json << 'EOF'
{ "key": "value" }
EOF
datum <command> --from-file ./spec.json
```

**Windows (PowerShell) 写文件：**
```powershell
'{ "key": "value" }' | Out-File -Encoding utf8 .\spec.json
datum <command> --from-file .\spec.json
```

## 升级 Skill

> 本节仅适用于 OpenCode 环境。检测方式：运行 `echo $OPENCODE`，输出为 `1` 则为 OpenCode。
> 其他工具（Claude Code、Cursor 等）的用户请通过 `git pull` 获取最新 skill 内容。

当用户要求升级或更新 datum-cli skill 时，先确认环境变量 `OPENCODE` 为 `1`，然后按以下步骤执行。如果不是 OpenCode 环境，告知用户通过 git pull 更新仓库后重新复制 skill 文件即可。

**第一步：检查版本**

根据平台执行对应的版本检查命令。

**Linux / macOS：**
```bash
LOCAL_VERSION=$(grep '^version:' ~/.config/opencode/skills/datum-cli/SKILL.md 2>/dev/null | awk '{print $2}' | tr -d '"')
REMOTE_VERSION=$(curl -fsSL https://cnbj1-fds.api.xiaomi.net/datum-cli/skill/latest/VERSION 2>/dev/null | tr -d '[:space:]')
echo "本地版本: ${LOCAL_VERSION:-未知}, 远程版本: ${REMOTE_VERSION:-获取失败}"
```

**Windows（PowerShell）：**
```powershell
$skillPath = "$env:USERPROFILE\.config\opencode\skills\datum-cli"
$local = (Select-String -Path "$skillPath\SKILL.md" -Pattern '^version:' | ForEach-Object { ($_ -split '\s+')[1].Trim('"') })
$remote = (Invoke-WebRequest -Uri "https://cnbj1-fds.api.xiaomi.net/datum-cli/skill/latest/VERSION" -UseBasicParsing).Content.Trim()
Write-Host "本地版本: $local, 远程版本: $remote"
```

**判断逻辑：**
- 远程版本获取失败 → 告知用户无法连接更新服务器，跳过升级
- 版本相同 → 告知用户 "datum-cli skill 已是最新版本 (version X)"，无需操作
- 版本不同 → 告知用户发现新版本，询问是否更新，用户确认后执行下方升级命令

**第二步：下载并安装（用户确认后执行）**

**Linux / macOS：**
```bash
SKILL_DIR=~/.config/opencode/skills

# 备份
cp -r "$SKILL_DIR/datum-cli" "$SKILL_DIR/datum-cli.bak"

# 下载并解压（zip 内含 datum-cli/ 前缀）
curl -fsSL "https://cnbj1-fds.api.xiaomi.net/datum-cli/skill/latest/datum-cli.zip" -o /tmp/datum-cli-skill.zip
unzip -o /tmp/datum-cli-skill.zip -d "$SKILL_DIR"
rm -f /tmp/datum-cli-skill.zip

# 验证
NEW_VERSION=$(grep '^version:' "$SKILL_DIR/datum-cli/SKILL.md" | awk '{print $2}' | tr -d '"')
echo "升级完成: ${LOCAL_VERSION} -> ${NEW_VERSION}，请重启 opencode 生效"
```

**Windows（PowerShell）：**
```powershell
$skillDir = "$env:USERPROFILE\.config\opencode\skills"
$zipPath = "$env:TEMP\datum-cli-skill.zip"

# 备份
Copy-Item -Recurse -Force "$skillDir\datum-cli" "$skillDir\datum-cli.bak"

# 下载并解压
Invoke-WebRequest -Uri "https://cnbj1-fds.api.xiaomi.net/datum-cli/skill/latest/datum-cli.zip" -OutFile $zipPath
Expand-Archive -Force -Path $zipPath -DestinationPath $skillDir
Remove-Item $zipPath

# 验证
$newVer = (Select-String -Path "$skillDir\datum-cli\SKILL.md" -Pattern '^version:' | ForEach-Object { ($_ -split '\s+')[1].Trim('"') })
Write-Host "升级完成: $local -> $newVer，请重启 opencode 生效"
```

> **回滚：** 如果升级出现问题，可用备份恢复。Linux/macOS: `rm -rf ~/.config/opencode/skills/datum-cli && mv ~/.config/opencode/skills/datum-cli.bak ~/.config/opencode/skills/datum-cli`；Windows: `Remove-Item -Recurse "$env:USERPROFILE\.config\opencode\skills\datum-cli"; Rename-Item "$env:USERPROFILE\.config\opencode\skills\datum-cli.bak" "datum-cli"`

## 常见错误处理

| 错误信息 | 原因 | 解决方式 |
|---------|------|---------|
| `no token configured` | 未配置 token | 运行 `datum config add` 或设置 `DATUM_TOKEN` 环境变量 |
| `404 Not Found` | 对象不存在 | 先用 `list` 确认名称，注意区分英文名和中文名 |
| `profile not found` | profile 名称错误 | 运行 `datum config list` 查看所有可用 profile |
| `--from-file is required` | 需要 JSON 文件 | 先将 JSON 内容写入临时文件，再传 `--from-file ./spec.json` |

