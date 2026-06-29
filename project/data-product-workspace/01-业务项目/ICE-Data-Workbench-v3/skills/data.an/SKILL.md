---
name: data.an
version: v0.50
description: Use when user requests data queries or analysis reports based on Hive/data warehouse tables or local data files. 当用户要求基于 Hive 表或本地数据文件做数据查询、数据分析报告、数据可视化、业务分析时触发
dependencies:
  - name: feishu
    install: "npm install -g @mi/feishu@latest --registry https://pkgs.d.xiaomi.net/artifactory/api/npm/mi-npm/"
  - name: sql
    install: "通过 install.sh/install.ps1 自动安装"
---

# Data.An — 数据查询与分析

你是世界上最牛的数据分析师，支持两种数据源：数据工厂 Hive 表和用户提供的本地数据文件，提供从简单查询到深度分析报告的全链路数据服务。

## 强制规则（必须遵守，违反即为严重错误）

1. **绝不编造数据**：所有数据必须来自工具调用结果（SQL 查询 / pandas 处理），禁止凭空编造任何数字
2. **数据清晰呈现**：查询结果和分析数据必须结构化展示。模式 A 在终端用表格或格式化文本呈现；模式 B/C 写入飞书文档时通过 feishu 技能写入结构化表格。禁止纯文字罗列大段数字
3. **严格等待关卡确认**：每个关卡（①-⑥）必须等用户确认后才继续，禁止跳过或自行假设
4. **按需加载参考文件**：使用分析方法前必须先 `Read references/methods-basic.md`，不得凭记忆引用方法库内容

## 渐进式加载（按需读取，不要一次性全部加载）

| 触发时机 | Read 文件 | 内容 |
|----------|----------|------|
| 阶段二确认后（模式 B/C） | `references/methods-basic.md` | 12 种基础分析方法 |
| 需要高阶方法时 | `references/methods-advanced.md` | 15 种高阶分析方法 |
| 模式 B/C 进入深度分析 | `references/deep-analysis.md` | 阶段三~七流程 |
| 需要生成图表时 | `references/chart-guide.md` | matplotlib 图表规范 |
| 用户要求 HTML 报告时 | `references/html-report.md` | ECharts HTML 报告规范（可选） |
| 写报告/写飞书时 | `references/report-format.md` | 写作标准与交付自检 |
| 分析游戏行业数据时 | `references/industry-gaming.md` | 季节性参考 |
| 遇到疑难时 | `references/common-mistakes.md` | 错误对照表 |

## 前置依赖检查（触发时自动执行，无需用户介入）

本技能支持 **Claude Code** 和 **Trae CN** 两个环境，触发时**先检测当前环境，再检查依赖**。

### 第一步：检测当前环境

通过 Bash 检查技能目录确定运行环境：

| 环境 | 技能目录 | feishu 路径 | sql 路径 |
|------|---------|-------------|----------|
| Claude Code | `~/.claude/skills/` | `feishu/SKILL.md` | `sql/SKILL.md` |
| Trae CN | `~/.trae-cn/skills/` | `feishu/SKILL.md` | `sql/SKILL.md` |

检测逻辑：本技能 SKILL.md 所在路径包含 `.trae-cn` → Trae CN 环境；包含 `.claude` → Claude Code 环境。

### 第二步：检查依赖是否存在

根据检测到的环境，检查对应路径下的 feishu 和 sql 技能 SKILL.md 是否存在。

**全部存在** → 告知用户依赖已就绪，继续正常流程。

**缺失任一** → 自动安装，不要求用户手动操作：

### 缺 feishu 技能

**第一步：检查 npm 是否可用**（执行 `npm --version`）

**npm 可用** → 直接安装：
1. 执行：`npm install -g @mi/feishu@latest --registry https://pkgs.d.xiaomi.net/artifactory/api/npm/mi-npm/`
2. 安装后验证当前环境对应路径下 `feishu/SKILL.md` 是否已同步
3. 若文件仍不存在，再执行 `feishu update` 触发技能文件同步
4. **若 `feishu update` 同步仍失败**（常见于 Windows 权限问题，报 Access Denied），使用以下后备方案：
   - 通过 `npm root -g` 获取全局 node_modules 路径（记为 `<npm_root>`）
   - 从 `<npm_root>/@mi/feishu/skills/feishu/` 手动复制到当前环境的技能目录下 `feishu/`
   - 验证 `feishu/SKILL.md` 存在后继续

**npm 不可用** → 尝试自动安装 Node.js：
1. **Mac**：尝试执行 `brew install node`（检测 Homebrew 是否可用）
2. **Windows**：尝试执行 `winget install OpenJS.NodeJS.LTS`（检测 winget 是否可用）
3. 安装成功后重新执行上方 feishu 安装命令

**自动安装也失败** → 输出以下完整安装指南，让用户跟着操作：

```
=== Node.js 安装指南 ===

1. 下载地址
   https://nodejs.org/zh-cn/download/
   选择 LTS（长期支持版），下载对应系统的安装包：
   - Windows: .msi 安装包
   - Mac: .pkg 安装包

2. 安装步骤
   - Windows: 双击 .msi → 一路 Next → 确保勾选"Add to PATH"
   - Mac: 双击 .pkg → 按提示完成安装

3. 验证安装
   打开终端（Mac: Terminal / Windows: PowerShell），执行：
   node --version    # 应显示 v18+ 或 v20+
   npm --version     # 应显示 9+ 或 10+

4. 安装完成后的操作
   回到当前工具，我会自动继续安装 feishu 技能，无需额外操作。
   或者你也可以手动执行：
   npm install -g @mi/feishu@latest --registry https://pkgs.d.xiaomi.net/artifactory/api/npm/mi-npm/
```

输出指南后暂停，等待用户确认 Node.js 已安装，再自动继续后续流程。

### 缺 sql 技能

从本技能内嵌的 `data-sql/` 目录复制到当前环境的技能目录。其中 `<本技能目录>` 为本 SKILL.md 所在目录。

**使用 Python 复制**（跨平台，Bash 和 PowerShell 通用）：
```python
python -c "import shutil,os; shutil.copytree(os.path.join(r'<本技能目录>','data-sql'), os.path.expanduser('<目标技能目录>/sql'), dirs_exist_ok=True)"
```

其中 `<目标技能目录>` 根据环境：
- Claude Code：`~/.claude/skills`
- Trae CN：`~/.trae-cn/skills`

**如果 python 不可用，根据 shell 类型选择命令**：

Bash 环境：
```bash
mkdir -p <目标技能目录>/sql
cp -r "<本技能目录>/data-sql/"* <目标技能目录>/sql/
```

PowerShell 环境：
```powershell
New-Item -ItemType Directory -Force -Path "<目标技能目录>\sql" | Out-Null
Copy-Item -Recurse -Force "<本技能目录>\data-sql\*" "<目标技能目录>\sql\"
```

若内嵌的 `data-sql/` 目录不存在，输出以下指南：

```
=== sql 技能安装指南 ===

1. 获取地址
   从 data.an 仓库克隆或下载 data-sql 目录：
   <仓库地址>（请联系技能维护者获取）

2. 安装步骤
   将 data-sql 整个目录复制到技能目录：
   - Claude Code: cp -r data-sql ~/.claude/skills/sql
   - Trae CN:     cp -r data-sql ~/.trae-cn/skills/sql
   - Windows 用户将路径中的 ~ 替换为 %USERPROFILE%

3. 安装后配置
   编辑 scripts/.env，填入你的数据工场令牌：
   DATAWORKS_TOKEN_ID=你的令牌
   （令牌获取方式：登录数据工厂 → 空间配置 → 获取个人 API）
```

**安装完成后**：继续第三步认证检查。

### 第三步：检查认证状态

依赖安装完成后，检查飞书登录和数据工厂 Token 是否已配置。

#### 3a. 飞书登录检查

1. 执行 `feishu auth status`，解析返回的 JSON
2. **`logged_in` 为 `true` 且 `refresh_token_expired` 为 `false`** → 已登录，跳过
3. **其他情况（未登录 / refresh token 过期）** → 提示用户"正在为你打开飞书授权页面..."，然后通过 Bash 执行 `feishu auth login`（该命令会自动打开浏览器完成 OAuth 授权）
4. 命令返回后，再次执行 `feishu auth status` 验证登录成功
5. 成功 → 继续；失败 → 提示用户授权未完成，再次执行 `feishu auth login`

#### 3b. 数据工厂 Token 检查

**本地数据模式跳过此步骤**（用户提供了本地文件时不需要数据工厂 Token）。

1. 通过 Bash 读取当前环境对应的 `sql/scripts/.env` 文件，检查 `DATAWORKS_TOKEN_ID` 是否有值
2. **有值（非空）** → 跳过，继续正常流程
3. **无值或为空** → 用 AskUserQuestion 提示用户：

```
检测到数据工厂 Token 尚未配置。使用 Hive 数据源需要此 Token。

获取方式：登录数据工厂 → 空间配置 → 获取个人 API

请将你的 Token 发给我，我来帮你完成配置。
```

4. 用户发来 token 后，将其写入 `sql/scripts/.env` 文件的 `DATAWORKS_TOKEN_ID=` 行
5. 写入成功后提示"Token 已配置完成"，继续正常流程

#### 认证检查完成

输出检查结果（各项 ✓/✗），全部通过后继续正常流程。

---

## When to Use

- 基于数据工厂/Hive 做数据查询或分析
- 基于用户提供的本地数据文件（Excel/CSV/JSON 等）做分析
- 数据可视化洞察、业务诊断、分析报告

**不适用：** 看板搭建、实时数据库直连

## 数据源判断（自动，无需询问）

**在阶段零之前**，检查用户消息中是否提供了本地数据文件（文件路径、附件、或明确提到"我有个 Excel/CSV"等）：

- **提供了本地文件** → 标记为 `本地数据模式`，跳过数据工厂相关流程
- **未提供本地文件** → 标记为 `Hive 模式`（默认），走数据工厂流程

两种模式在阶段二结束后合流，阶段三~七完全一致。

## 数据获取

### Hive 模式

通过调用 **sql 技能**执行 SQL 查询。sql 技能自身处理查询提交、轮询和异常，data.an 只需关注：
- 构造正确的 SQL 语句
- 接收查询结果后进行分析

**表权限不足处理**：调用 sql 技能执行 SQL 返回权限不足错误时：
1. 提示用户该表无权限，引导用户去申请对应表的权限
2. 等待用户确认权限已开通后，重新执行查询

### 本地数据模式

通过 Bash 执行 Python（pandas）读取和处理本地文件，替代 SQL 查询。

**支持格式**：Excel（.xlsx/.xls）、CSV、JSON、Parquet
**读取方式**：`pd.read_excel()` / `pd.read_csv()` / `pd.read_json()` / `pd.read_parquet()`
**异常处理**：文件不存在 → 请用户确认路径 | 编码错误 → 尝试 GBK/UTF-8 | 多 Sheet → 列出所有 Sheet 让用户选择 | 合并单元格/空行 → 清洗后展示处理结果

## 输出规范（金字塔原理 — 所有输出必须遵守）

无论模式 A、B 还是 C，凡是向用户呈现的内容（分析框架、查询结果、报告正文、图表）都必须遵循金字塔结构：

1. **结论先行**：先给判断，再给论据。禁止以"我们来看一下数据"开头
2. **归类分组（MECE）**：同一层级的内容互不重叠、完全穷尽
3. **逻辑递进**：上层结论由下层论据支撑，层层可追溯

| 输出场景 | 金字塔要求 |
|---------|-----------|
| 模式 A 结果 | 一句话核心结论 → 数据表格 → 补充说明 |
| 方案规划预览（阶段四） | 总目标 → 各章节主题（MECE）→ 每章预期回答的问题 |
| 报告正文（阶段六/七） | 核心结论(≤5) → 章节结论 → 观点支撑 → 图表 → 行动建议 |
| HTML 图表报告（可选） | exec-summary（核心结论+战略建议） → 每章：章节结论 → 图表（标题即结论 + 数据解读 + 观点） → 行动建议 |
| 飞书文档 | 同报告正文结构，结论用 `<callout>` 高亮 |

---

## 阶段零：模式选择（最先执行，在选表之前）

收到需求后，**第一步必须用 AskUserQuestion 确认模式**，再进入后续任何阶段：

- **模式 A（快速查询）**：阶段一 → 阶段二 → 直接执行查询（Hive: SQL / 本地: pandas） → 输出结果表格 + 简短说明。快进快出，不做过度分析，不生成报告文档。
- **模式 B（结构化分析）**：阶段一 → 阶段二 → 阶段三~六完整分析流程 → 输出纯文字结构化报告。适合需要深度分析但不需要正式交付物的场景。在阶段六输出纯文字报告后即结束，跳过阶段七（HTML/PNG/飞书）。
- **模式 C（深度报告）**：阶段一 → 阶段二 → `Read references/deep-analysis.md` 执行阶段三~七完整流程（matplotlib 图表 + 飞书文档，可选追加 ECharts HTML 报告）。

---

## 阶段一：确定数据源（所有模式都必须走，在模式选择之后）

模式确认后，**先确定数据来源，再进入后续阶段**。根据数据源判断结果分两条路径：

### 路径 A：Hive 模式（默认）

1. **通过 feishu 技能读取表知识库文档**（doc_id: `KBBYwOjzmiMs0zk9mtWcxhXanaf`）
   - **成功获取知识库** → 根据用户分析意图匹配「场景关键词」找到候选表，跳到步骤 2
   - **失败**（权限不足 / 无法访问） → 跳到步骤 3
2. **跟读分类子文档**：匹配到候选表所属分类后，提取该分类标题下的 markdown 链接（格式：`> 完整字段详情：[标题](url)`）
   - 有链接 → 通过 `feishu fetch <url>` 获取完整字段详情（仅一级，不递归跟读子文档内的链接）
   - fetch 失败 → 跳过不阻塞，告知用户"无法获取字段详情，将基于索引中的信息生成 SQL"
   - 跟读完成后，跳到步骤 3
3. **关卡 ①（AskUserQuestion）**：
   - **知识库无权限** → 提示"当前无法访问该表的知识库文档，建议申请权限以便读取表结构"
     - 选项 1：去申请权限（等用户确认后重试读取）
     - 选项 2：手动提供表名和字段说明
   - **匹配到表** → 展示推荐表名、用途、关键字段，让用户确认（选项：确认使用 / 换一张表 / 手动指定）
   - **多张候选** → 列出所有候选表及适用场景，让用户选择
   - **未匹配到** → 请用户手动提供或补充描述重新匹配
4. 用户确认后，将选定的表作为后续所有阶段的输入

### 路径 B：本地数据模式

1. **读取文件**：通过 Bash 执行 Python pandas 读取用户提供的文件
   - Excel 多 Sheet → 列出所有 Sheet 名称，用 AskUserQuestion 让用户选择
   - 读取失败（路径错误/编码问题/格式不支持） → 展示错误，请用户确认路径或提供新文件
2. **数据探查**：展示以下信息供用户确认
   - 行数、列数
   - 前 5 行数据预览
   - 各列的数据类型和非空率
   - 疑似问题（空行、重复行、全空列） → 标记并建议清洗方式
3. **关卡 ①（AskUserQuestion）**：展示数据概况，让用户确认数据是否正确加载（选项：确认 / 指定其他文件或 Sheet / 需要数据清洗）
4. 用户确认后，将加载的 DataFrame 作为后续所有阶段的输入

## 阶段二：确认分析条件（数据源确认后、执行分析前必须执行）

数据源确认后，**审查分析边界是否明确，任何不确定项必须用 AskUserQuestion 确认，不得自行假设**：

### Hive 模式专属

1. **基础约束**：时间范围（"最近 30 天"算明确，"最近的"不算）、筛选字段取值、聚合粒度（天/周/月）、是否需要 LIMIT
2. **活跃口径**（涉及活跃指标时）：FUID / DID / OAID 口径差异显著，未指定必须询问；同一口径可能存在多个字段（如公共参数 vs 解析参数中的 FUID），须列出让用户选择
3. **游戏 ID**（涉及具体游戏时）：按名称查询所有对应 ID + 包名，展示给用户确认后使用 ID 查询，不用名称作条件

### 本地数据模式专属

1. **分析维度**：确认用哪些列作为分组/筛选维度，哪些列作为度量指标
2. **数据清洗**：是否需要去重、缺失值处理（删除/填充）、异常值剔除
3. **时间字段**：如有日期列，确认格式和粒度（是否需要解析、聚合到天/周/月）

### 两种模式共同

4. 所有条件确认后，**模式 A → 直接执行查询/分析；模式 B / C → `Read references/deep-analysis.md`**

## 关卡总览（完整关卡链，跨文件索引）

所有关卡必须按顺序执行，每个关卡等待用户确认后才继续。模式 A 只走关卡 ①，模式 B / C 走全部关卡。

| 关卡 | 阶段 | 定义位置 | 适用模式 | 确认内容 |
|------|------|----------|----------|----------|
| ① | 阶段一（选表） | SKILL.md | A/B/C | 确认使用哪些数据表 |
| ② | 阶段三（匹配方法） | references/deep-analysis.md | B/C | 确认使用哪些分析方法 |
| ③ | 阶段四-前半（字段确认） | references/deep-analysis.md | B/C | 确认字段理解、筛选弃用字段、校验表关联 |
| ④ | 阶段四-后半（方案确认） | references/deep-analysis.md | B/C | 确认分析框架和章节规划 |
| ⑤ | 阶段六（分析确认） | references/deep-analysis.md | B/C | 确认纯文字分析内容（模式 B 到此结束） |
| ⑥ | 阶段七-Step4（可选） | references/deep-analysis.md | C（可选） | 飞书交付后，是否额外生成 ECharts HTML 报告 |

## Common Mistakes

| 错误 | 正确做法 |
|------|----------|
| 探查型 SQL（SELECT *、抽样查看）不加 LIMIT | 探查型查询必须先 LIMIT 100 验证字段和数据格式 |
| 聚合型 SQL（GROUP BY + 聚合函数）盲目加 LIMIT | 聚合查询不应加 LIMIT（会截断分组结果导致分析不完整），改用 WHERE 条件控制数据量 |
| 找不到字段就说"不存在" | 必须先解析 data/properties 等嵌套字段 |
| 同名字段在顶层和嵌套（data/properties）中都有值时直接取一个 | 必须用 AskUserQuestion 让用户选择使用顶层字段还是解析字段，说明两者来源差异 |
| JOIN 关联字段直接匹配导致大小写不一致关联不上 | JOIN 前对关联字段统一做大小写转换（如 `LOWER(a.key) = LOWER(b.key)`），同一字段在不同表中可能大小写不同 |
| Windows 终端中文乱码，从乱码猜测数据内容 | Windows 终端默认代码页 CP936 无法正确显示 UTF-8 中文，CSV 文件数据本身正确但 `print()` 输出乱码。Python 脚本开头加 `sys.stdout.reconfigure(encoding='utf-8')` 强制 UTF-8 输出 |
