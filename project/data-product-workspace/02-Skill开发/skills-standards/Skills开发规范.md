# Skills 开发规范

> 基于对 `/Users/mi/.micode/skills/` 目录下全部 25 个 Skills 的系统性分析，提炼出的开发规范。

---

## 一、目录结构规范

### 1.1 标准目录

每个 Skill 必须遵循以下目录结构：

```
<skill-name>/
├── SKILL.md          # 必需，Skill 主文件
├── scripts/          # 可选，可执行脚本
├── references/       # 可选，参考文档（按需加载到上下文）
└── assets/           # 可选，输出资源（模板、图标、字体等）
```

**关键约定**：
- 主文件名统一为 `SKILL.md`（大写），个别旧 Skill 使用 `skill.md`（小写），新 Skill 应统一使用大写
- `scripts/`、`references/`、`assets/` 即使当前为空也必须创建，保持结构标准化
- 禁止创建 `README.md`、`INSTALLATION_GUIDE.md`、`CHANGELOG.md` 等辅助文档，Skill 只包含 AI Agent 执行任务所需的信息

### 1.2 references 的组织方式

references 目录支持两种组织模式：

**模式 A：扁平结构**（适用于领域单一的 Skill）
```
references/
├── api_guide.md
├── metrics_definition.md
└── metric_name_mapping.md
```

**模式 B：按业务线/领域分子目录**（适用于多业务线的 Skill）
```
reference/
├── browser-main/
│   ├── core-metrics-tables.md
│   ├── metric-name-index.md
│   └── event-name-index.md
├── browser-feed/
│   ├── browser-core-metrics.md
│   └── browser-event-reference.md
├── content-center/
│   └── ...
├── search/
│   └── ...
└── novel/
    └── ...
```

**模式 C：按功能/变体分子目录**（适用于多框架/多平台的 Skill）
```
references/
├── aws.md
├── gcp.md
└── azure.md
```

### 1.3 scripts 的组织方式

```
scripts/
├── <主功能脚本>.py        # 核心执行脚本
├── <辅助脚本>.py          # 辅助工具
├── requirements.txt       # Python 依赖（如有）
└── .env                   # 环境变量模板（如有）
```

---

## 二、SKILL.md 编写规范

### 2.1 Frontmatter 格式

SKILL.md 必须以 YAML frontmatter 开头，包含 `name` 和 `description` 两个必需字段：

```yaml
---
name: "skill-name"
description: "功能描述 + 触发场景 + 适用条件"
---
```

**description 编写要求**（这是 Skill 被触发的核心依据）：

1. **必须包含功能描述**：清晰说明 Skill 做什么
2. **必须包含触发场景**：明确什么情况下应该使用此 Skill
3. **必须包含不适用场景**（可选但推荐）：说明什么情况下不应使用
4. **所有"何时使用"的信息必须放在 description 中**，而非 body 中——因为 body 仅在 Skill 触发后才加载

**优秀 description 示例**：

```yaml
description: 内容生态信息流业务的核心指标自助分析 Agent。支持五个业务线（浏览器主端、浏览器信息流、内容中心、搜索、小说），覆盖核心指标与埋点数据两种查询类型。当用户需要查询业务数据、分析核心指标或埋点事件数据、生成分析报告并输出到飞书文档时使用此技能。触发场景：当用户明确提到 "执行 auto-analysis"、"使用 auto-analysis" 时，必须且只能使用本技能；用户提到"数据分析"、"指标分析"、"生成报告"、"飞书报告"等也要使用本技能。
```

**反面示例**（过于简略）：
```yaml
description: "Generates illustrations for articles"
```

### 2.2 Body 结构模板

SKILL.md 的 Body 应按以下结构组织：

```markdown
# Skill 名称

## 角色定位（可选）
简要描述 Skill 扮演的角色和专业领域。

## 功能描述
清晰说明 Skill 的核心功能和能力边界。

## 适用场景
- 场景 1
- 场景 2

## 不适用场景（推荐）
- 场景 A
- 场景 B

## 执行流程（核心）
详细描述 Skill 的标准执行步骤，必须按顺序编号。

## 检验条件（推荐）
列出每个关键步骤的校验规则。

## 异常处理（推荐）
列出常见异常及处理方式。

## 使用示例
提供 2-3 个典型使用示例。

## 扩展建议（可选）
说明如何扩展 Skill 的能力。
```

### 2.3 执行流程编写规范

执行流程是 SKILL.md 的核心，必须遵循以下规范：

1. **步骤必须编号且有序**：使用"第一步"、"第二步"或"Step 1"、"Step 2"格式
2. **每步必须说明输入和输出**：明确该步骤需要什么信息、产出什么结果
3. **必须标注强制步骤**：用 ⚠️ 或 ⛔ 标记不可跳过的步骤
4. **交互模板必须完整**：涉及用户交互时，提供完整的对话模板
5. **分支逻辑必须清晰**：使用条件判断时，用表格或流程图说明

**执行流程示例**：

```markdown
### 第一步：收集用户信息

向用户询问以下信息：
1. **实验组版本号**
2. **对照组版本号**
3. **分析时间周期**

**交互模板**：
> 请提供版本灰度数据所在的文件夹路径。

**确认信息模板**：
> 收到，确认实验分析参数如下：
> - 实验组：{实验组版本号}
> - 对照组：{对照组版本号}
> - 时间范围：{开始日期} 至 {结束日期}
```

### 2.4 渐进式披露原则

SKILL.md 应遵循三层加载设计：

| 层级 | 内容 | 加载时机 | 大小限制 |
|------|------|---------|---------|
| 元数据 | name + description | 始终在上下文中 | ~100 词 |
| SKILL.md Body | 核心工作流和指引 | Skill 触发时 | <500 行 / <5k 词 |
| references/ | 详细参考文档 | 按需加载 | 无限制 |

**关键原则**：
- SKILL.md Body 控制在 500 行以内，超出时拆分到 references 文件
- SKILL.md 中只保留核心流程指引，详细规范移入 references
- 在 SKILL.md 中明确标注何时需要读取哪个 reference 文件
- 避免深层嵌套引用，references 应与 SKILL.md 直接关联（一层深度）

---

## 三、脚本开发规范

### 3.1 脚本设计原则

1. **确定性优先**：重复性操作、易出错操作必须封装为脚本
2. **参数化设计**：脚本应通过命令行参数接收输入，避免硬编码
3. **幂等性**：相同输入应产生相同输出
4. **错误自描述**：错误信息应包含足够上下文便于排查

### 3.2 脚本调用规范

```bash
# 标准调用格式
python3 <skill-dir>/scripts/<script>.py <参数>

# 带环境变量的调用
DATAWORKS_TOKEN_ID=xxx python3 <skill-dir>/scripts/<script>.py "SQL语句"

# 从文件读取输入
python3 <skill-dir>/scripts/<script>.py --file input.sql
```

**关键约定**：
- 脚本必须从项目根目录执行，不要 `cd` 到脚本目录
- 使用绝对路径引用脚本
- 环境变量通过前缀方式传入，不写入代码

### 3.3 脚本输出规范

- 小结果集（≤15行）：直接返回表格格式
- 大结果集（>15行）：自动保存为 CSV 文件并返回文件路径
- 空结果：返回明确的提示信息
- 执行错误：返回详细错误信息（包含错误类型、原因、建议修复方式）

### 3.4 依赖管理

```
scripts/
├── requirements.txt    # Python 依赖清单
└── .env               # 环境变量模板（不包含真实密钥）
```

- `requirements.txt` 必须列出所有 Python 依赖及最低版本
- `.env` 仅作为模板，真实密钥通过环境变量或用户交互获取
- 禁止在代码中硬编码 API Key、Token 等敏感信息

---

## 四、参考资料编写规范

### 4.1 参考资料分类

| 类型 | 用途 | 示例 |
|------|------|------|
| 索引文件 | 快速校验指标/事件是否在支持范围内 | `metric-name-index.md`、`event-name-index.md` |
| 定义文件 | 详细说明指标口径、计算公式 | `metrics_definition.md`、`metric_name_mapping.md` |
| 模板文件 | 提供可复用的 SQL/代码模板 | `dashboard_metrics.sql` |
| API 文档 | 外部 API 的使用说明 | `api_guide.md`、`extended-markdown.md` |
| 规则文件 | 领域特定的规则和最佳实践 | `3d.md`、`animations.md` |

### 4.2 索引文件编写规范

索引文件用于快速校验，应满足：
- 内容结构化，便于程序化匹配
- 包含完整的指标/事件列表
- 标注每个条目的唯一标识（如指标 ID）
- 标注所属模块/分类

### 4.3 长文件规范

超过 100 行的 reference 文件必须在顶部包含目录（Table of Contents），便于 Agent 快速了解文件全貌。

---

## 五、环境与认证规范

### 5.1 环境变量

| 场景 | 环境变量 | 说明 |
|------|---------|------|
| Google API | `GOOGLE_API_KEY` / `GEMINI_API_KEY` | 图像生成、NotebookLM |
| 数据查询 | `DATAWORKS_TOKEN_ID` | DataWorks 数据库访问 |
| 飞书 | 自动管理 | feishu CLI 自动处理 token 刷新 |

### 5.2 认证流程标准

1. **首次使用前检查**：执行环境检查命令
2. **缺失时引导用户**：通过 AskUserQuestion 工具询问
3. **保存配置**：将用户提供的认证信息保存到本地配置文件
4. **后续静默跳过**：已有有效认证时不再打扰用户

---

## 六、输出规范

### 6.1 文件命名规范

- SQL 文件：`{模块名}.sql` 或 `{前缀}_query.sql`
- 数据文件：`{模块名}.csv` 或 `{前缀}_data.csv`
- 分析报告：`{前缀}_analysis.md`
- 图表文件：`{前缀}_chart.png`
- 目录命名：`{YYYYMMDD}_{HHMMSS}_{关键词}`

### 6.2 报告输出规范

1. **指标名称必须使用中文**：通过映射表将英文字段名转换为中文
2. **按维度分模块展示**：如按用户类型（大盘/老用户/新用户）分模块
3. **完整性要求**：禁止省略任何模块、任何指标的数据
4. **结构化呈现**：使用表格、汇总表、分天明细等层次化展示

### 6.3 飞书文档输出规范

- 写入前必须读取 `feishu` Skill 的 `reference/extended-markdown.md`
- 使用分块 append 方式写入，避免单次超长写入失败
- 内容去重后再写入
- 使用 Callout 高亮关键信息
- 用分割线、表格打破大段纯文字
