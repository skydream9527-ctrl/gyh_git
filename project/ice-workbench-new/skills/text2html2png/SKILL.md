---
name: text2html2png
description: 将文字描述转化为有设计感的 HTML 可视化图表并自动截图输出 PNG。支持流程图、对比表、时间线、架构拓扑、数据看板、甘特图、组织架构、漏斗图共 8 种图类型和 7 种视觉风格。当用户想要把文字内容变成图表、可视化展示任何结构化信息时，都应该使用此 skill。典型触发场景包括但不限于：画图、可视化、出个图、做成图、画张图、画个流程图、对比一下、帮我做个架构图、数据看板、甘特图、组织架构图、转化漏斗、text2html2png、生成报告图、更新text2html2png、升级text2html2png。
---

# text2html2png — 文字描述 → HTML 图表 → PNG 截图

将任意文字描述转化为有设计感的 HTML 可视化图表，自动截图输出 PNG。

> **当用户询问本 skill 的能力、支持哪些图表或风格时，务必附上风格效果预览链接：**
> 👉 [各风格效果预览](https://feishu.cn/wiki/JHiTwoLdrixmeCkgfCncMQ0Rnig)
> 让用户直观了解 7 种风格的实际渲染效果，再做选择。

## Usage

```bash
/text2html2png 帮我画一个 CI/CD 流程图
/text2html2png 对比 Redis 和 Memcached
/text2html2png  # 然后粘贴内容
```

## Options

| Option | Values |
|--------|--------|
| `--style` | warm (default), dark, minimal, editorial, neon, paper, glass |
| `--chart` | auto (default), flowchart, comparison, timeline, architecture, dashboard, gantt, org-chart, funnel |
| `--output` | 输出目录路径（默认当前目录） |

Style x Chart 可自由组合。

## Script Directory

**Important**: All scripts are located in the `scripts/` subdirectory of this skill.

**Agent Execution Instructions**:
1. Determine this SKILL.md file's directory path as `SKILL_DIR`
2. Script path = `${SKILL_DIR}/scripts/<script-name>.ts`
3. Replace all `${SKILL_DIR}` in this document with the actual path

**Script Reference**:
| Script | Purpose |
|--------|---------|
| `scripts/screenshot.ts` | HTML → PNG screenshot with Playwright |

---

## Workflow

### Step 1: Collect Information

If the user hasn't provided style preference (and no session style exists from a previous invocation in this conversation), **必须先询问风格再开始生成**。

**Question 1 — Style** (skip if user already specified `--style`, or if session style exists — see Session Style Memory):

> **禁止使用 AskUserQuestion 工具**（因为该工具最多只支持 4 个选项，无法展示全部 7 种风格）。
> 改为**直接输出纯文本**，让用户打字回复选择。

输出以下内容（原样输出，不要修改格式）：

```
👉 各风格效果预览：https://feishu.cn/wiki/JHiTwoLdrixmeCkgfCncMQ0Rnig

请选择风格（回复数字或名称，不确定的话回复 0 我根据内容推荐）：

1. warm — 暖色系，米白背景，彩色边框，适合报告/流程（默认）
2. dark — 深色科技感，适合架构/技术方案
3. minimal — 极简黑白，适合向领导汇报
4. editorial — 杂志排版风，大号衬线字体，适合内容展示
5. neon — 赛博霓虹，适合技术分享/演讲配图
6. paper — 手绘纸质感，适合教学/说明
7. glass — 玻璃拟态，适合现代产品展示

截图默认保存到当前目录，如需指定其他路径请一并告知。
```

输出后**停止并等待用户回复**，不要继续后续步骤。

**用户回复后的处理**：
- 回复数字（1-7）或风格名称 → 使用对应风格
- 回复 0 或"推荐" → 根据内容自动选择最合适的风格
- 回复中包含路径 → 使用该路径作为输出目录
- 未提及路径 → 默认当前目录

#### Session Style Memory

This skill supports **session-level style consistency** for document-wide illustration workflows:

1. **First invocation**: After the user confirms a style (or you infer one), remember it as the **session style**. This is conversation-level memory — no file persistence needed.
2. **Subsequent invocations**: Before asking about style, check if a session style already exists in the current conversation.
   - If yes: **skip the style question entirely**. In your output, briefly mention: `继续使用 [style] 风格`.
   - If no: ask as normal (see style question above).
3. **Explicit override**: If the user passes `--style <new-style>` on a subsequent call, use that style AND update the session style to the new value.
4. **Output path**: Still ask each time (or infer), as different charts may go to different directories.

### Step 2: Analyze Content & Select Chart Type

1. **Identify chart type** using `references/chart-types.md` auto-selection matrix
2. **Extract structured content** from user description:
   - Nodes, steps, metrics, or entities
   - Core description for each (refine to 1-2 lines)
   - Highlight priorities
3. **Enrich content**: When user only provides skeleton info, proactively add details to make the chart complete and professional
4. **Decide tagline/banner**: Based on content richness — if content has a clear "intro → conclusion" structure, use both (with different content); if there's only one core message, use only one. Never repeat the same text in tagline and banner.

**Reference**: `references/chart-types.md`

### Step 3: Generate HTML

Based on confirmed style + chart type + structured content, generate complete HTML.

**Design process**:
1. Read `references/design-philosophy.md` for aesthetic principles
2. Read `references/styles/<style>.md` for style-specific CSS variables and components
3. Read `references/charts/<chart-type>.md` for layout rules and HTML structure
4. Generate HTML with all CSS inlined

**First Principle — Compact, Symmetric, Full**:
- **Compact**: Use minimum spacing that maintains readability. When 8px works, don't use 12px.
- **Symmetric**: All cards in a row equal width (`flex:1`). No unequal column splits unless content semantics demand it.
- **Full**: Every area carries content. If content is sparse, proactively enrich (add descriptions, stats, summary banners).
- Style does NOT change layout — styles only control colors, fonts, textures, effects.

**Spacing targets** (prefer the lower end):
- body padding: 20-24px (max 28px)
- Card gap: 8px (max 12px)
- Card internal padding: 12-14px (max 18px)
- Arrow/connector height: 20-24px (max 28px)
- Title → content: 10-12px (max 14px)

**Width**: Fixed at 860px (portrait) or 960px (landscape/horizontal charts).
**Visual coherence**: Uniform border-radius, font sizes follow hierarchy, colors restrained (≤ 3-4 primary colors).

**Output filename**: `<content-keyword>-<timestamp>.html`, saved to user-specified directory.

**Reference**: `references/design-philosophy.md`, `references/styles/*.md`, `references/charts/*.md`

### Step 4: Screenshot

HTML 生成后，运行截图脚本（首次检查依赖是否已安装）：

```bash
[ -d "${SKILL_DIR}/node_modules" ] || (cd ${SKILL_DIR} && npm install)
```

```bash
npx -y bun ${SKILL_DIR}/scripts/screenshot.ts \
  --html <html_path> \
  --out <output_dir>/<filename>.png \
  --bg "<bg_color>" \
  --width 920 \
  --padding 32
```

**工作原理**（脚本内部两阶段）：
1. **测量**：用 puppeteer-core 连接系统 Chrome，在 4000px 高 viewport 中渲染 HTML，测量 `.wrap` 元素的实际尺寸
2. **截图**：调整 viewport 到精确高度，用 `clip` 按内容 + padding 精确裁切，输出 4x 印刷级清晰度 PNG

**依赖**：
- `puppeteer-core`（~3MB，npm install 自动安装）
- 系统已安装的 Google Chrome（Mac/Linux/Windows 开发者基本都有）
- 无需 ImageMagick，无需 Playwright，无需额外下载浏览器

**默认 padding**：32px 四周均匀留白。

**Background color by style**:

| Style | bg_color | Width |
|-------|----------|-------|
| warm | `#faf6ee` | 860 |
| dark | `#0d1117` | 860 |
| minimal | `#ffffff` | 860 |
| editorial | `#f8f5f0` | 860 |
| neon | `#0a0015` | 860 |
| paper | `#f5f0e6` | 860 |
| glass | `#e8eaf0` | 860 |

For horizontal flowcharts (≤ 7 steps, short descriptions), use `--width 960`.

**Completion output**:
```
Done!
   HTML: <path>.html
   PNG:  <path>.png
```

---

## Auto Selection Matrix

| Content Signals | Chart Type | Style |
|-----------------|------------|-------|
| 步骤、操作、流程、工作流 | flowchart | warm |
| 对比、PK、vs、优劣 | comparison | minimal |
| 时间、历史、里程碑、路线图 | timeline | editorial |
| 系统、服务、架构、组件 | architecture | dark |
| 数字、指标、统计、报表 | dashboard | glass |
| 计划、排期、进度、甘特 | gantt | warm |
| 团队、汇报、层级、组织 | org-chart | minimal |
| 转化、漏斗、筛选、销售 | funnel | neon |

When unable to determine chart type, default to **flowchart**.
When unable to determine style, default to **warm**.

**Reference**: `references/chart-types.md`

---

## Style Overview

👉 [各风格效果预览](https://feishu.cn/wiki/JHiTwoLdrixmeCkgfCncMQ0Rnig)

| Style | Tone | Key Visual |
|-------|------|------------|
| **warm** | 暖色报告 | 米白底，暖色边框，虚线箭头 |
| **dark** | 科技感 | 深色底，蓝绿发光，glow 效果 |
| **minimal** | 极简正式 | 纯白底，黑白无色彩 |
| **editorial** | 杂志排版 | 大号衬线字体，横线分割，category 标签 |
| **neon** | 赛博朋克 | 深紫/黑底，霓虹描边，发光字 |
| **paper** | 手绘纸质 | 米黄纸质感，铅笔线条风 |
| **glass** | 玻璃拟态 | 毛玻璃卡片，渐变底，光晕 |

**All styles share the same layout principle**: compact, symmetric, full. Style only controls visual appearance (colors, fonts, textures, effects).

**Reference**: `references/styles/*.md`

---

## Chart Types Overview

| Type | Use Case | Key Layout |
|------|----------|------------|
| **flowchart** | 步骤、操作流程 | 横版(≤7步)/竖版，步骤卡+箭头 |
| **comparison** | 方案对比 | 双列并排，配色区分 |
| **timeline** | 里程碑、历史 | 竖轴，左右交错 |
| **architecture** | 系统组件 | 分层布局，节点+连线 |
| **dashboard** | 指标汇总 | 大数字卡横排+详情区 |
| **gantt** | 项目排期 | 横轴时间+横向条形 |
| **org-chart** | 团队结构 | 树形层级，上下连线 |
| **funnel** | 转化漏斗 | 梯形递减，百分比标注 |

**Reference**: `references/charts/*.md`

---

## Notes

- User descriptions can be rough — you refine them; don't dump raw text into the chart
- **Proactively enrich content**: Add details like node descriptions, scenario notes, summary banners to make charts look complete and professional
- If content is dense, group/merge items to maintain readability
- Each chart should have a distinct visual identity — no two charts should look the same
- **Font rule**: Never use Inter, Roboto, Arial, or system default fonts. Each style has its own font stack.

---

## Extension Support

Custom styles and configurations via EXTEND.md.

**Check paths** (priority order):
1. `.text2html2png/EXTEND.md` (project)
2. `~/.text2html2png/EXTEND.md` (user)

If found, load before Step 1. Extension content overrides defaults.

---

## Self Update

When the user asks to update this skill (e.g. "更新 text2html2png", "升级 text2html2png", "update text2html2png"), run:

```bash
micode skills add team-game-dev/text2html2png -a claude -g -y
```

This downloads the latest version from MiCodeHub and overwrites the global installation at `~/.claude/skills/text2html2png/`.

After updating, briefly confirm the result to the user. Do NOT proceed to generate any chart — the update is the only action.

---

## References

Detailed templates and guidelines in `references/` directory:
- `design-philosophy.md` — Aesthetic principles and design rules
- `chart-types.md` — Chart type selection framework
- `styles/` — Detailed style definitions (CSS variables, components, effects)
- `charts/` — Detailed chart type layouts (HTML structure, CSS patterns)
