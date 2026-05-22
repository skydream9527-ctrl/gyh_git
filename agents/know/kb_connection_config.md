# 知识库连接配置手册

本文件供 AI Agent 读取，使其能够自主连接飞书知识库和 Mify RAG 知识库，完成文档读写、搜索、同步等操作。

---

## 一、飞书知识库

### 1.1 连接方式

通过飞书 CLI（`feishu`）操作，CLI 自动管理 token 刷新，无需手动处理认证。

### 1.2 安装

```bash
npm install -g @mi/feishu@latest --registry https://pkgs.d.xiaomi.net/artifactory/api/npm/mi-npm/
```

验证安装：

```bash
feishu --version   # 当前版本 1.2.1
```

### 1.3 认证

```bash
feishu auth login    # 首次使用，浏览器 OAuth 登录
feishu auth status   # 检查登录状态
feishu auth logout   # 清除 token
```

认证成功后 `auth status` 返回：

```json
{
  "logged_in": true,
  "access_token_expired": false,
  "refresh_token_expired": false
}
```

Token 自动刷新，refresh token 有效期 30 天。过期需重新 `feishu auth login`。

### 1.4 目标知识库信息

| 字段 | 值 |
|------|-----|
| 知识库名称 | 内容生态数据产品知识库 |
| space_id | `7560912865739997187` |
| 用途 | 内容生态部门数据产品方向的文档、规范、SQL、案例、复盘等知识资产沉淀 |

### 1.5 知识库目录结构

目录结构在飞书侧持续变动，**不要把树状图固化在本文件里**。需要时按下列方式实时获取：

```bash
# 列出根节点
feishu wiki nodes 7560912865739997187

# 进入指定节点查看子节点
feishu wiki nodes 7560912865739997187 --parent <node_token>
```

高频访问的 wiki_token 写入 agent memory `reference_frequent_tokens.md`（参见 `prompt/system.md` 中的 Context 机制约定）。

### 1.6 常用操作速查

#### 读取文档

```bash
feishu fetch "https://mi.feishu.cn/wiki/TOKEN"        # 自动识别类型
feishu fetch "https://mi.feishu.cn/docx/TOKEN"        # 读取文档
feishu fetch "URL" --download-images ./assets          # 下载图片
```

#### 写入知识库

```bash
# 在指定节点下创建新文档
feishu docx create "标题" -f content.md --wiki-node NODE_TOKEN

# 在知识空间根目录创建
feishu docx create "标题" -c "# 内容" --wiki-space SPACE_ID

# 追加内容（推荐，非破坏性）
feishu docx update "URL" --mode append -c "## 新章节"

# 替换指定内容
feishu docx update "URL" --mode replace --select "旧内容...结尾" -c "新内容"

# 覆盖全文（破坏性，慎用，需 --force）
feishu docx update "URL" --mode overwrite --force -f content.md
```

#### 浏览知识库

```bash
feishu wiki spaces                                    # 列出所有知识空间
feishu wiki nodes SPACE_ID                            # 列出根节点
feishu wiki nodes SPACE_ID --parent NODE_TOKEN        # 列出子节点
feishu wiki get "https://mi.feishu.cn/wiki/TOKEN"    # 获取节点详情
```

#### 搜索

```bash
feishu search "关键词"
feishu search "关键词" --sort edit_time
```

### 1.7 写入规范

- 写入前先读取飞书扩展 Markdown 语法参考：`~/.trae-cn/skills/feishu/reference/extended-markdown.md`
- 标题层级 ≤ 4 层，用 Callout 高亮关键信息
- 优先使用 `append`/`replace`，避免 `overwrite`
- 非 TTY 环境下 overwrite 必须加 `--force`

---

## 二、Mify RAG 知识库

### 2.1 连接方式

通过 Mify Skill 脚本操作，基于 API Key 认证，支持本地文件和飞书文档作为数据源。

### 2.2 Skill 安装

```bash
micode skills add ai-team/mify-knowledge-base -y
```

Skill 路径：

| 工具 | 路径 |
|------|------|
| Trae | `~/.trae-cn/skills/mify-knowledge-base/` |
| 其他 | `~/.agents/skills/mify-knowledge-base/` |

### 2.3 配置文件

#### 全局配置（禁止提交，含敏感信息）

路径：`~/.mify/config.json`

```json
{
  "email": "<your-email>@xiaomi.com",
  "default_profile": "default-space",
  "profiles": {
    "default-space": { "api_key": "dataset-<your-api-key>" }
  }
}
```

| 字段 | 说明 |
|------|------|
| email | 飞书邮箱，飞书操作时必需 |
| default_profile | 默认 Profile 名称 |
| profiles | 各空间的 API Key，格式 `dataset-xxx` |

API Key 获取地址：https://mify.mioffice.cn/datasets?category=api

#### 项目级配置（可提交，团队共享）

路径：`.mify/config.json`（项目根目录下）

```json
{
  "default_profile": "default-space",
  "search_profiles": ["default-space"]
}
```

| 字段 | 说明 |
|------|------|
| default_profile | 项目默认 Profile |
| search_profiles | 搜索时扫描的 Profile 列表，支持跨空间搜索 |

### 2.4 当前知识库信息

本 agent **默认不绑定任何 Mify RAG 知识库**——唯一目标是飞书空间「内容生态数据产品知识库」。Mify 工具（`mify_search` / `mify_upload`）保留为可选语义检索能力，调用时必须显式传 `kb_name`。如果团队后续需要把内容生态空间同步到 Mify，再到 `agents/know/config.py` 的 `MIFY_KNOWLEDGE_BASES` 中登记。

### 2.5 操作前必须执行预检

```bash
SKILL_DIR="$HOME/.trae-cn/skills/mify-knowledge-base"

# 本地操作
python3 "$SKILL_DIR/scripts/preflight.py"

# 涉及飞书操作
python3 "$SKILL_DIR/scripts/preflight.py" --need-email --verify-feishu

# 指定 Profile
python3 "$SKILL_DIR/scripts/preflight.py" --profile default-space
```

预检返回 `ready: true` 才能继续，否则按 `errors` 逐项修复。

### 2.6 常用操作速查

#### 知识库管理

```bash
SKILL_DIR="$HOME/.trae-cn/skills/mify-knowledge-base"

# 列出所有知识库
python3 "$SKILL_DIR/scripts/list_knowledge_bases.py" list

# 创建知识库
python3 "$SKILL_DIR/scripts/list_knowledge_bases.py" create \
  --name "名称" --description "描述" --permission all_team_members

# 查看知识库内文档
python3 "$SKILL_DIR/scripts/list_knowledge_bases.py" docs --kb "名称"
```

#### 上传文档

```bash
# 本地文件
python3 "$SKILL_DIR/scripts/create_documents.py" local --kb "名称" --dir ./docs

# 飞书文档（3 步）
python3 "$SKILL_DIR/scripts/preflight.py" --need-email --verify-feishu
python3 "$SKILL_DIR/scripts/create_documents.py" crawl --urls "https://mi.feishu.cn/wiki/TOKEN"
python3 "$SKILL_DIR/scripts/create_documents.py" feishu --kb "名称" --urls "https://..."
```

支持的文件类型：`.txt` `.md` `.pdf` `.html` `.xlsx` `.docx` `.csv`

#### 更新文档

```bash
# 本地文件（自动检测变更）
python3 "$SKILL_DIR/scripts/update_documents.py" local --kb "名称" --dir ./docs

# 同步所有飞书文档
python3 "$SKILL_DIR/scripts/update_documents.py" feishu-sync --kb "名称" --all
```

#### 搜索

```bash
# 基本搜索（hybrid_search + reranking，top 5）
python3 "$SKILL_DIR/scripts/search_knowledge_base.py" --kb "名称" --query "关键词"

# 更多结果
python3 "$SKILL_DIR/scripts/search_knowledge_base.py" --kb "名称" --query "关键词" --top-k 10

# 指定 Profile
python3 "$SKILL_DIR/scripts/search_knowledge_base.py" --kb "名称" --query "关键词" --profile default-space
```

### 2.7 数据存储

| 路径 | 可提交 | 说明 |
|------|--------|------|
| `~/.mify/config.json` | 否 | 个人配置（API Key、邮箱） |
| `~/.mify/state/{profile}/kb-registry.json` | 否 | 知识库列表缓存 |
| `~/.mify/state/{profile}/feishu-{token}.json` | 否 | 飞书爬取结果（3天过期） |
| `.mify/config.json` | 是 | 项目设置 |
| `.mify/state/{profile}/{kb_id}.json` | 是 | 本地文件上传追踪 |

### 2.8 注意事项

- 所有脚本必须从**项目根目录**执行，禁止 `cd` 到 skill 目录
- 搜索白名单修改必须经用户确认，AI 禁止自主修改
- 飞书操作前必须验证 `feishu_bound: true`
- 爬取超时可用 `--timeout 600`，深度不足可用 `--max-depth 8`

---

## 三、两个知识库的协作关系

```
┌─────────────────────────────────────────────────────────┐
│                    AI Agent                              │
│                                                         │
│  ┌──────────────────┐    ┌──────────────────────────┐  │
│  │   飞书知识库       │    │   Mify RAG 知识库         │  │
│  │                  │    │                          │  │
│  │  用途：           │    │  用途：                   │  │
│  │  · 人工阅读/协作   │    │  · AI 语义检索           │  │
│  │  · 结构化文档展示  │    │  · RAG 问答              │  │
│  │  · 团队知识共享    │    │  · 知识召回与生成         │  │
│  │                  │    │                          │  │
│  │  工具：feishu CLI │    │  工具：Mify Skill 脚本    │  │
│  │  认证：OAuth 登录  │    │  认证：API Key           │  │
│  │  space_id:       │    │  profile: default-space  │  │
│  │  763111270937...  │    │                          │  │
│  └──────────────────┘    └──────────────────────────┘  │
│                                                         │
│  典型工作流：                                            │
│  1. feishu fetch 读取飞书文档 → 整理内容                 │
│  2. feishu docx create 写入飞书知识库（人工可读）         │
│  3. mify create_documents feishu 导入 Mify（AI 可检索）  │
│  4. mify search_knowledge_base 语义搜索（AI 问答）       │
└─────────────────────────────────────────────────────────┘
```

### 推荐同步策略

| 场景 | 飞书知识库 | Mify 知识库 |
|------|-----------|------------|
| 新文档入库 | `docx create` 创建结构化页面 | `create_documents feishu` 导入为 RAG 数据源 |
| 内容更新 | `docx update --mode replace` 局部更新 | `update_documents feishu-sync --all` 全量同步 |
| 信息检索 | `feishu search` 关键词搜索 | `search_knowledge_base` 语义检索 |
| 团队协作 | 人工阅读、评论、编辑 | AI 自动召回、生成回答 |

---

## 四、新 Agent 接入 Checklist

新 AI Agent 读取本文件后，按以下步骤验证连接：

### 飞书知识库

- [ ] 检查 `feishu` CLI 是否可用：`feishu --version`
- [ ] 检查认证状态：`feishu auth status`（`logged_in: true`）
- [ ] 验证知识库可访问：`feishu wiki nodes 7560912865739997187`
- [ ] 测试搜索：`feishu search "数据产品"`（应能命中至少一篇空间内文档）

### Mify 知识库（可选，本 agent 默认不绑定）

仅在团队登记了与本空间对应的 Mify KB 后才需校验：

- [ ] 检查全局配置：`cat ~/.mify/config.json`（需含 email 和 api_key）
- [ ] 检查项目配置：`cat .mify/config.json`（需含 default_profile 和 search_profiles）
- [ ] 运行预检：`python3 ~/.trae-cn/skills/mify-knowledge-base/scripts/preflight.py`（`ready: true`）
