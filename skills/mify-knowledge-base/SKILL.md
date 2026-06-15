---
name: mify-knowledge-base
description: 管理 Mify 知识库 — 列表、创建、上传文档、更新和搜索。支持本地文件上传和飞书文档集成。
version: 2.3.1
---

# Mify 知识库管理

管理 Mify 知识库全生命周期：创建知识库、上传文档（本地文件和飞书）、变更检测更新、搜索。支持多 API Key Profile 和跨 Profile 搜索。

## 用户交互方式

需要向用户收集信息或确认时，根据当前环境选择：

- **Claude Code**：使用 `AskUserQuestion` tool，按下方示例格式调用
- **其他工具**（Cursor、Windsurf、普通对话等）：在文本回复中直接列出选项，等待用户回复

下文中所有「向用户询问」的示例均以 `AskUserQuestion` 格式描述。在不支持该 tool 的环境中，将同等内容改为文本提问即可，交互逻辑不变。

## 关键规则：必须从项目根目录执行

**所有脚本必须从项目根目录执行。** 禁止 `cd` 到 skill 目录或其子目录。脚本依赖当前工作目录读取 `.mify/config.json` 等状态文件，切换目录会导致读取失败。

```bash
# 正确 — 在项目根目录执行，使用脚本完整路径
python "path/to/skill/scripts/list_knowledge_bases.py" list

# 错误 — 禁止 cd 到 skill 目录
cd <path/to/skill/scripts> && python list_knowledge_bases.py list
```

## 初始配置

创建 `~/.mify/config.json`，包含邮箱、API Key 和 Profile：

```bash
mkdir -p ~/.mify
cat > ~/.mify/config.json << 'EOF'
{
  "email": "your-name@company.com",
  "default_profile": "default-space",
  "profiles": {
    "default-space": { "api_key": "dataset-your-api-key-here" }
  }
}
EOF
```

所有脚本会自动检测此全局配置。如需多个 API Key（如不同团队），在 `profiles` 中添加多个条目，通过 `--profile <name>` 切换。

### 配置缺失时的提示

配置不存在时，向用户收集信息：

```
questions:
  - question: "请提供 Mify API Key（格式：dataset-xxxx，在 Mify 设置页获取）"
    header: "API Key"
    options:
      - label: "我还没有 API Key"
        description: "前往 https://mify.mioffice.cn/datasets?category=api 获取"
    multiSelect: false
```

若需邮箱（飞书操作），追加第二个问题：

```
  - question: "请提供飞书邮箱地址（飞书同步时需要）"
    header: "邮箱"
    options:
      - label: "跳过（稍后配置）"
        description: "仅本地操作时可跳过"
    multiSelect: false
```

用户选择"其他"时会输入自定义值（即 API Key / 邮箱），用该值创建配置。

### 旧版配置兼容

如果项目 `.mify/config.json` 中直接包含 `api_key`（旧格式），系统仍可识别，自动作为 `_legacy` Profile。建议迁移：将 API Key 移至 `~/.mify/config.json` 的 `profiles` 中。

## 预检（每次操作前必须执行）

执行任何脚本前，先运行预检脚本：

```bash
# 仅本地操作：
python "<skill-dir>/scripts/preflight.py"
# 飞书操作（需邮箱 + 验证飞书绑定）：
python "<skill-dir>/scripts/preflight.py" --need-email --verify-feishu
# 指定 Profile：
python "<skill-dir>/scripts/preflight.py" --profile default-space
```

输出 JSON 状态：

```json
{
  "config_exists": true,
  "api_key": true,
  "email": "user@example.com",
  "profile_name": "default-space",
  "profile_exists": true,
  "active_kbs": ["KB1", "KB2"],
  "registry_exists": true,
  "kb_count": 2,
  "kbs": [
    {"name": "My KB", "id": "xxx", "description": "产品文档和使用指南", "doc_count": 5}
  ],
  "zombies": [],
  "warnings": [],
  "feishu_bound": true,
  "feishu_auth_url": null,
  "ready": true,
  "errors": []
}
```

**字段说明：**

| 字段                     | 含义                                                         |
| ------------------------ | ------------------------------------------------------------ |
| `active_kbs` = `null`    | 所有知识库均可搜索（无限制）                                 |
| `active_kbs` = `[]`      | 搜索已**禁用**                                               |
| `active_kbs` = `["KB1"]` | 仅白名单中的知识库可搜索                                     |
| `profile_name`           | 解析后的 Profile 名称（如 `"default-space"` 或旧版的 `"_legacy"`） |
| `profile_exists`         | Profile 是否在 `~/.mify/config.json` 的 `profiles` 中定义    |
| `zombies`                | 卡在 `uploading`/`updating` 状态的文档（中断的上传），每项包含 `kb_id`、`doc_name`、`doc_id`、`status` |
| `warnings`               | 可读的警告信息，无问题时为空数组                             |
| `feishu_bound`           | 仅 `--verify-feishu` 时出现。`true` = 飞书已绑定；`false` = 需通过 `feishu_auth_url` 授权 |

**结果处理：**

- `ready: true` → 继续操作
- `ready: false` → 读取 `errors` 数组逐项修复：
  - **配置未找到** → 向用户索取 `api_key`（飞书操作还需 `email`），创建配置
  - **api_key 为空** → 向用户索取有效 Key
  - **邮箱缺失**（`--need-email` 时） → 向用户索取邮箱
  - **Registry 未找到** → 执行 `list_knowledge_bases.py list` 刷新，再重新预检
  - **飞书未绑定** → 按「飞书授权流程」处理
- 发现 zombies 时，建议执行 `sync-state` 或 `purge` 清理

### 飞书授权流程

当 `feishu_bound` 为 `false`（或爬取时出现认证错误）时，向用户引导授权：

```
questions:
  - question: "飞书尚未授权。请在浏览器中打开授权链接完成绑定，然后选择「已完成授权」：\n\n授权链接：<feishu_auth_url>"
    header: "飞书授权"
    options:
      - label: "已完成授权"
        description: "已在浏览器中点击"授权"并等待页面跳转完成"
      - label: "需要帮助"
        description: "不确定如何操作或遇到问题"
    multiSelect: false
```

用户选择「已完成授权」后，运行验证：

```bash
python "<skill-dir>/scripts/preflight.py" --need-email --verify-feishu
```

- `feishu_bound: true` → 绑定成功，继续操作
- `feishu_bound: false` → 绑定失败，参考故障排除

**禁止跳过验证** — 飞书操作前必须用 `--verify-feishu` 确认绑定状态。

## 确定目标知识库

需要目标知识库时（上传、更新、搜索），按以下顺序操作：

### 1. Profile 选择（多 Profile 时必须询问）

**多 Profile 判断方法**：读取 `~/.mify/config.json` 中的 `profiles` 字段，若包含多个条目，必须让用户选择目标空间。

- **仅一个 Profile** → 自动使用，无需询问
- **多个 Profile** → 向用户列出选项让其选择：

```
questions:
  - question: "你有多个 Mify 空间，请选择要操作的空间："
    header: "空间"
    options:
      - label: "default-space"
        description: "Profile: default-space"
      - label: "shared-docs"
        description: "Profile: shared-docs"
    multiSelect: false
```

> 根据实际 Profile 列表动态生成 options（最多 4 个；超过 4 个时列出前 3 个常用的，第 4 个用"输入 Profile 名称"让用户通过"其他"自行填写）。

### 2. 知识库选择（合并可见范围，一次交互完成）

**展示预检 `kbs` 列表，同时将新建知识库的推断结果一并呈现，让用户一次选择。**

- 有飞书爬取结果时：先爬取，再从文档标题推断新知识库名称、描述、可见范围（默认推断为团队可见）
- 无论上传方式如何，禁止自动创建或自动选择知识库

根据实际 kbs 列表动态生成选项（AskUserQuestion 格式示例）：

```
questions:
  - question: "找到 76 篇文档。请选择目标知识库："
    header: "知识库"
    options:
      - label: "Mi Code CLI 使用说明书"
        description: "已有知识库，当前 9 篇文档"
      - label: "HI-UI"
        description: "已有知识库，当前 1 篇文档"
      - label: "新建「KeyCenter 文档」"
        description: "团队可见 — 如需调整名称/描述/可见范围，请选择"其他"说明"
    multiSelect: false
```

> 动态生成规则：已有 KB 按文档数降序排列，最后一项为推断的新建选项。超过 3 个已有 KB 时，选取最相关的 2-3 个（按名称与文档内容匹配度），剩余 KB 可通过"其他"输入名称选择。

用户选择新建时，若通过"其他"输入了特殊要求则按用户说明调整，否则直接使用推断值创建，**无需再次确认**。

### 知识库命名规范

新建知识库时，必须设置**有意义的名称和描述**，禁止使用通用名称如"My KB"或"Test"。

**名称推断规则（按优先级）：**

1. **用户明确指定** → 直接使用
2. **从项目上下文推断** → 读取 `package.json` / `pyproject.toml` / `Cargo.toml` 中的 name 字段、Git remote URL 的仓库名、当前目录名
3. **从上传内容推断** → 根据文件/目录主题推断（如 `api-docs/` → "API 文档"）
4. **从飞书爬取结果推断** → 分析文档标题共性主题，Wiki 容器从标题共享关键词推断，单个文档直接使用标题

**可见范围默认值：** 无法推断时默认为团队可见（`all_team_members`），在选择提示中明确标注，用户可在选择时覆盖。

## 搜索白名单修改策略（强制）

**任何搜索白名单（`active_kbs`）的修改必须经用户明确确认后执行。** AI 严禁自主执行白名单修改命令，包括 `--set`、`--add`、`--remove`、`--clear`、`--disable`。

**流程：** 向用户确认变更（AskUserQuestion 格式示例）：

```
questions:
  - question: "搜索白名单变更确认：\n\n当前白名单：KB1, KB2\n变更操作：添加「KB3」\n变更后：KB1, KB2, KB3\n\n是否执行？"
    header: "白名单"
    options:
      - label: "确认执行"
        description: "执行上述白名单变更"
      - label: "取消"
        description: "不做任何修改"
    multiSelect: false
```

用户选择「确认执行」后才执行对应命令。

## 脚本参考

所有脚本在 `scripts/` 目录中，**必须从项目根目录用完整路径执行**。

### `preflight.py`

预检 — 验证配置、API Key、邮箱和知识库 Registry。输出 JSON 状态。

```bash
python preflight.py
python preflight.py --need-email --verify-feishu
python preflight.py --profile default-space
```

### `list_knowledge_bases.py`

列出知识库、创建知识库、管理搜索配置和本地状态。

**子命令：** `list`、`docs`、`create`、`search-config`、`sync-state`、`purge`

```bash
# 列出所有知识库（同时刷新本地 Registry）
python list_knowledge_bases.py list
python list_knowledge_bases.py list --hide-empty

# 列出知识库内所有文档
python list_knowledge_bases.py docs --kb "名称"
python list_knowledge_bases.py docs --kb "名称" --feishu-only   # 只看飞书来源文档

# 创建知识库
python list_knowledge_bases.py create --name "名称" --description "描述"
python list_knowledge_bases.py create --name "名称" --description "描述" --permission all_team_members
python list_knowledge_bases.py create --name "名称" --description "描述" --provider mibrag

# 查看搜索白名单
python list_knowledge_bases.py search-config

# 白名单修改（必须经用户确认）
python list_knowledge_bases.py search-config --set "KB1" "KB2"   # 替换白名单
python list_knowledge_bases.py search-config --add "KB3"          # 添加到白名单
python list_knowledge_bases.py search-config --remove "KB1"       # 从白名单移除
python list_knowledge_bases.py search-config --clear               # 移除白名单（所有知识库可搜索）
python list_knowledge_bases.py search-config --disable             # 禁用搜索（白名单设为空）

# 状态同步 — 将本地追踪与远端文档对齐
python list_knowledge_bases.py sync-state --kb "名称"

# 清除本地状态
python list_knowledge_bases.py purge --kb "名称"
```

`sync-state` 输出 JSON：`{kb_id, synced（匹配数）, added（新增远端文档数）, orphaned（本地孤立数）}`

### `create_documents.py`

添加文档到知识库。来源：本地文件或飞书。

**子命令：** `local`、`feishu`、`crawl`、`status`、`purge-feishu`

> `feishu` 子命令上传前会自动对比 KB 已有文档，跳过 `doc_token` 相同的文档，重复执行同一 URL 不会产生重复文档。

```bash
# 上传本地目录中的文件
python create_documents.py local --kb "名称" --dir ./docs

# 爬取飞书链接（仅保存元数据，不创建文档）
python create_documents.py crawl --urls "https://xxx.feishu.cn/wiki/TOKEN"
python create_documents.py crawl --urls "https://xxx.feishu.cn/wiki/TOKEN" --timeout 600 --max-depth 8

# 查看已缓存的爬取状态（无需重新爬取）
python create_documents.py status --token TOKEN
python create_documents.py status --url "https://xxx.feishu.cn/wiki/TOKEN"

# 从飞书链接创建文档（自动读取缓存的爬取结果，无缓存时自动爬取）
# 默认设置 3 天自动同步
python create_documents.py feishu --kb "名称" --urls "https://xxx.feishu.cn/wiki/TOKEN"
python create_documents.py feishu --kb "名称" --urls "..." --timeout 300 --max-depth 6

# 清除飞书爬取缓存
python create_documents.py purge-feishu --token TOKEN
```

**`status` 输出示例：**

```
Token:      VmMHwoQ01iH7Vvk547RcFEGvn5Z
URL:        https://mi.feishu.cn/wiki/VmMHwoQ01iH7Vvk547RcFEGvn5Z
Crawled at: 2026-03-11T03:20:21.335017+00:00
Cache:      valid (0 day(s) ago)
Docs:       76

Documents:
    1. [docx] SID 权限查询-申请和管理
    2. [docx] kc server 压力测试
    ...
```

缓存过期时显示 `Cache: EXPIRED (4 day(s) ago)`，提示重新爬取。

**爬取选项**（`crawl` 和 `feishu` 子命令）：

- `--timeout <秒>`：单次爬取请求超时（默认 180，最大 3600）
- `--max-depth <层>`：Wiki 容器递归展开最大深度（默认 4）

**支持的文件类型：** `.txt`、`.md`、`.pdf`、`.html`、`.xlsx`、`.docx`、`.csv`

### `update_documents.py`

更新已有文档。本地文件通过 SHA256 哈希检测变更。

**子命令：** `local`、`feishu-sync`、`set-frequency`

```bash
# 更新本地变更文件（跳过未变更）
python update_documents.py local --kb "名称" --dir ./docs

# 同步 KB 内所有飞书文档（推荐，无需指定文档 ID）
python update_documents.py feishu-sync --kb "名称" --all

# 同步指定飞书文档（需邮箱）
python update_documents.py feishu-sync --kb "名称" --doc-ids DOC_ID_1 DOC_ID_2

# 设置飞书文档自动同步频率（需邮箱）
python update_documents.py set-frequency --kb "名称" --frequency 3 --doc-ids DOC_ID_1 DOC_ID_2
```

> `feishu-sync` 支持两种模式：`--all` 自动发现并同步 KB 内全部飞书文档（推荐）；`--doc-ids` 指定同步特定文档（文档 ID 可在 `.mify/state/{profile}/{kb_id}.json` 或创建文档时的 API 响应中找到）。`--all` 与 `--doc-ids` 互斥。

### `search_knowledge_base.py`

搜索知识库。`--kb` 必填。脚本自动通过 `search_profiles` 路由到正确的 Profile。

```bash
# 默认搜索（hybrid_search、reranking、top 5）
python search_knowledge_base.py --kb "名称" --query "查询内容"
python search_knowledge_base.py --kb "名称" --query "查询" --top-k 10
python search_knowledge_base.py --kb "名称" --query "查询" --no-rerank
python search_knowledge_base.py --kb "名称" --query "查询" --profile default-space
```

**自动路由**：未指定 `--profile` 时，脚本从 `search_profiles`（回退到 `[default_profile]`）扫描各 Profile 的 `kb-registry.json`，首个匹配即用该 Profile 的 API Key 搜索。

在项目配置中设置 `search_profiles` 包含所有可搜索的 Profile：

```json
{
  "search_profiles": ["default-space", "shared-docs"]
}
```

#### 搜索流程（每次搜索前必须遵循）

1. **运行预检** — 获取 `kbs` 列表和 `active_kbs` 白名单，通过 `description` 判断哪个知识库最相关
2. **选择知识库** — 根据描述匹配用户意图，或使用用户指定的知识库
3. **检查白名单** — 搜索脚本会检查 `active_kbs`。输出 `[BLOCKED]` 时，告知用户并询问是否添加到白名单（**禁止擅自添加**）
4. **执行搜索**

#### 搜索技巧

1. **每次查询用 2–3 个关键词** — 短而精准，如 `"添加 额外路径 工作区"` 而非长句
2. **3–4 次失败后放弃** — 列出尝试过的查询，告知用户未找到匹配内容，建议换关键词或换知识库

## 故障排除

### 飞书授权错误

爬取失败并提示 `[AUTH] Feishu authorization required` 时：

1. 运行 `preflight.py --need-email --verify-feishu`
2. 若 `feishu_bound: false`：引导用户在浏览器中打开 `feishu_auth_url` 完成授权
3. 用户授权后再次 `--verify-feishu` 验证

### 爬取超时

提示 `[WARN] Request timed out after Ns` 时，增大超时：

```bash
python create_documents.py crawl --urls "..." --timeout 600
```

### 爬取深度不足

提示未展开容器达到最大深度时，增大深度限制：

```bash
python create_documents.py crawl --urls "..." --max-depth 8
```

### 不确定 Token 是否已爬取

先用 `status` 查看缓存，避免重复爬取：

```bash
python create_documents.py status --token TOKEN
# 或
python create_documents.py status --url "https://..."
```

## 数据存储

### 全局目录（`~/.mify/`）— 禁止提交

存放个人配置和空间级状态：

```json
{
  "email": "you@company.com",
  "default_profile": "default-space",
  "profiles": {
    "default-space": { "api_key": "dataset-aaa" }
  }
}
```

| 文件 | 用途 |
|---|---|
| `~/.mify/config.json` | 个人配置：email、profiles（API Key） |
| `~/.mify/state/{profile}/kb-registry.json` | 知识库列表缓存（`list` 时自动更新） |
| `~/.mify/state/{profile}/feishu-{token}.json` | 飞书爬取结果（文档标题、类型、token、爬取时间，3 天自动过期） |

### 项目级（`.mify/`）

| 文件 | 可提交 | 用途 |
|---|---|---|
| `.mify/config.json` | **是** | 项目设置：`default_profile`、`search_profiles`、`active_kbs` |
| `.mify/.gitignore` | **是** | 自动创建，仅忽略 `state/**/*.tmp` |
| `.mify/state/{profile}/{kb_id}.json` | **是** | 本地文件追踪（ID、哈希、状态）— 仅含本地上传文档 |

### 协作指南

- **提交** `.mify/config.json` — 非敏感项目设置，团队共享搜索配置
- **提交** `.mify/state/{profile}/{kb_id}.json` — 本地文件追踪状态（KB 专用仓库场景下团队共享）
- **禁止提交** `~/.mify/` — 包含 API Key 和空间级状态
- **每位成员**需在自己的 `~/.mify/config.json` 中定义对应的 Profile 和 API Key

## 标准工作流

1. **预检** — `preflight.py`（本地）或 `preflight.py --need-email --verify-feishu`（飞书）
2. **修复问题** — `ready: false` 时按 `errors` 逐项修复
3. **列出/创建知识库** — `list_knowledge_bases.py list` 或 `create`
4. **添加文档** — `create_documents.py local/feishu/crawl`
5. **更新文档** — `update_documents.py local/feishu-sync/set-frequency`
6. **搜索** — 预检获取知识库描述，选择合适的知识库，`search_knowledge_base.py`

### 飞书专用流程（精简版，3 步）

1. **预检 + 验证授权**（自动）

   ```bash
   python preflight.py --need-email --verify-feishu
   ```

   - `feishu_bound: false` → 展示授权链接，等用户完成后重新验证
   - `feishu_bound: true` → 继续

2. **爬取 + 展示知识库选择**（一次交互）

   先检查是否有缓存（`status --url <url>`），无缓存则爬取：

   ```bash
   python create_documents.py crawl --urls "<url>"
   ```

   爬取完成后，**立即**展示知识库选择提示（含新建选项和推断的名称/可见范围），**等待用户选择一次即可**，无需再单独询问可见范围。

3. **创建/上传**（自动）

   ```bash
   # 新建知识库（如需）
   python list_knowledge_bases.py create --name "名称" --description "描述" --permission all_team_members

   # 上传文档
   python create_documents.py feishu --kb "名称" --urls "<url>"
   ```
