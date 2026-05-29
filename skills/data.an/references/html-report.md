# ECharts HTML 报告规范（可选，仅用户要求时加载）

> 本文件仅在阶段七 Step 4 用户选择生成 HTML 报告时才需要加载。

HTML 报告不是图表合集，而是**包含完整结论、观点、建议的独立可阅读报告**。禁止"只有图表没有文字分析"的 HTML 报告。

---

## 单文件交付与 CDN 规范

- HTML 报告必须是**单文件交付**，不依赖本地图片或外部文件，分享一个 `.html` 即可完整展示
- 外部库（ECharts 等）统一使用**国内可访问的 CDN**：
  - ECharts: `https://cdn.bootcdn.net/ajax/libs/echarts/{version}/echarts.min.js`
  - 其他库优先选择 `cdn.bootcdn.net` / `unpkg.zhimg.com` / `cdn.staticfile.net`
- 禁止使用 `jsdelivr.net`、`unpkg.com` 等国内不稳定的 CDN

## 白色背景规范（飞书适配）

HTML 报告和所有图表必须使用**白色背景**，确保截图 PNG 插入飞书文档时风格统一：

- `body` 和报告容器背景色设为 `#ffffff`，禁止使用深色/暗黑主题
- ECharts 图表初始化时显式设置 `backgroundColor: '#ffffff'`
- 所有 `.chart-box`、`.kpi-card`、`.exec-summary` 等组件不得使用深色背景
- 文字颜色使用深色（`#333` / `#666`），确保白底上可读性

## 图表文字与可读性规范

**文字对比度（强制）**：文字颜色必须与背景形成足够对比，禁止出现"看不清"的情况：

- 白色/浅色背景 → 文字、坐标轴标签、图例、数据标签统一使用深色（`#333` / `#666`）
- ECharts 配置中显式设置 `axisLabel.color`、`legend.textStyle.color`、`title.textStyle.color`、`label.color`，不依赖默认值

**标签防遮挡（强制）**：图表中的数据标签、图例不得与坐标轴重叠：

- `grid` 配置预留足够边距（`left/right/bottom/top`），为长标签文字留出空间
- 柱状图/折线图的 `label.position` 设为 `'top'` 或 `'outside'`，避免标签落在坐标轴区域内
- 饼图/环形图设置 `avoidLabelOverlap: true`
- X 轴标签过长时使用 `axisLabel.rotate`（15-45度）或 `axisLabel.interval` 控制间隔
- 图例（legend）放在图表上方或下方，不与绘图区重叠；数据系列较多时使用 `legend.type: 'scroll'` 滚动图例

## HTML 报告整体结构

```
header（封面）→ kpi-grid（KPI 卡片）→ exec-summary（核心结论与战略建议）→ 各 section（分析章节）
```

## 组件规范

| 组件 | CSS class | 用途 | 内容要求 |
|------|-----------|------|----------|
| 封面 | `.header` | 报告标题、副标题、分析周期等元信息 | 标题 + 副标题 + meta（周期、口径、范围） |
| KPI 卡片 | `.kpi-grid` > `.kpi-card` | 全局关键指标概览 | 3-5 个指标，每个含 label、value、change（涨跌标色） |
| 核心结论与战略建议 | `.exec-summary` | 报告最高层结论，读者第一眼看到 | 核心结论列表（`.finding-list`）+ 核心矛盾（`.core-contradiction`）+ 战略建议卡片（`.strategy-grid` > `.strategy-card`） |
| 章节标题 | `.section-title` | 各分析章节分隔 | — |
| 章节结论 | `.conclusion-box` | 每章开头的结论判断句 | `<strong>章节结论：</strong>` + 一段话概括本章核心发现 |
| 图表区 | `.chart-box` | 图表 + 文字解读 | 标题（`h3`，即结论）+ 关键洞察（`.insight`，红色高亮）+ ECharts 图表 + 数据解读（`.analysis-text`） |
| 数据解读 | `.analysis-text` | 每个图表下方的文字分析 | `<strong>数据解读：</strong>` 客观描述数据 + `<strong>观点：</strong>` 分析师判断和建议 |
| 行动建议 | `.action-box` | 每章末尾的具体行动项 | `<strong>行动建议：</strong>` + 具体到人群、时间、动作的建议 |
| 战略建议卡片 | `.strategy-card` | exec-summary 中的战略建议 | 标题（`h4`）+ 描述（`p`，含具体策略） |
| 核心矛盾 | `.core-contradiction` | 提炼全局最突出的结构性问题 | 标题（`h3`）+ 一段话描述 |

## 每个图表的完整结构（不可省略）

```html
<div class="chart-box">
  <h3>图表标题（即结论判断句）</h3>
  <div class="insight">关键洞察（一句话，红色高亮）</div>
  <div id="chartN" class="chart"></div>
  <div class="analysis-text">
    <strong>数据解读：</strong>客观描述数据发现...<br>
    <strong>观点：</strong>分析师判断、原因分析、建议...
  </div>
</div>
```

## 图表选择

图表类型参见 `references/methods-basic.md` 和 `references/methods-advanced.md` 的「可视化」列。KPI 概览用数字卡片。一图一结论；超 6 类归合"其他"；精确数字用表格。关键波动用 `markPoint`/`markLine` 标注。时间趋势图须遵循季节性应用规则（`references/industry-gaming.md` 规则 #3），使用 `markArea` 标注寒暑假、`markLine` 标注节假日。

**桑基图**：ECharts 原生支持桑基图，适用于渠道归因（#5）、用户路径分析（#12）、跨渠道迁移（#19）等需要展示流向关系的场景。这是 HTML 报告相对 matplotlib 的独特优势。

## 报告结构

```
封面 → KPI 概览（独立区块）→ 核心结论与战略建议 → 背景与目标 → 数据说明 → 各分析章节
```

### 报告开头模块

紧跟封面，读者第一眼看到的内容：

1. **KPI 概览**（独立区块，在 exec-summary 之前）：3-5 个关键指标卡片（数字 + 变化趋势）
2. **核心结论与战略建议**（exec-summary）：
   - 核心结论（≤5 条）：每条一句话判断 + 关键数据支撑
   - 核心矛盾：提炼全局最突出的结构性矛盾（1-2 句话）
   - 战略建议（≤3 条）：卡片式，每条含标题 + 具体策略（到人群、时间、动作）
   - 关键行动项：最紧急的 3-5 个可执行动作

> 不再有末尾独立「总结与建议」章节。各分析章节末尾的 action-box 仅放该章局部建议。

## PNG 截图规范

### 调用方式

通过 Bash 执行 Node.js 一次性脚本调用 Puppeteer 或 Playwright：

1. **检测可用工具**：先 `npx puppeteer --version` 或 `npx playwright --version`，哪个可用用哪个
2. **Puppeteer 调用**：`node -e "const p=require('puppeteer'); ..."` 或写临时 `.js` 文件后 `node temp_screenshot.js`
3. **Playwright 调用**：`npx playwright screenshot --viewport-size=1440,900 --full-page report.html output.png`
4. **都不可用**：告知用户"当前环境无浏览器自动化工具，请手动打开 HTML 文件截图"，跳过 PNG 步骤

### 截图参数

- 固定宽度 1440px，`fullPage: true`，不设固定高度
- 截图前等待渲染完成（`waitUntil: 'networkidle0'` + 额外 2s delay 等待 ECharts 动画），超 16000px 高度按章节分段截图
- 单图截图用 `element.screenshot()`；截图后校验文件大小 > 0 且宽度 1440px

## HTML 交付自检

- [ ] HTML 报告文件存在且大小 > 0
- [ ] `报告全图.png` 存在且大小 > 0
- [ ] 每个 ECharts 图表都有 `analysis-text`（数据解读+观点）
- [ ] 每章有 `conclusion-box` 和 `action-box`
- [ ] 有 `exec-summary`（核心结论+战略建议）
- [ ] 时间趋势图遵循季节性规则（`markArea` 寒暑假 + `markLine` 节假日）
- [ ] ECharts 截图前等待渲染完成（`waitUntil: 'networkidle0'` + 额外 2s delay）
