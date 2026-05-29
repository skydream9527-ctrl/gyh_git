# Chart Type Selection Framework

## 8 Chart Types

| Type | ID | Use Case | Key Elements |
|------|----|----------|-------------|
| Flow Chart | `flowchart` | 步骤、操作流程、工作流、Pipeline | 有序步骤，箭头，先后关系 |
| Comparison | `comparison` | 方案 PK、优劣对比、A vs B | 双列并排，差异高亮 |
| Timeline | `timeline` | 里程碑、历史事件、路线图、版本迭代 | 时间轴，节点，左右交错 |
| Architecture | `architecture` | 系统组件、服务依赖、模块划分、网络拓扑 | 分层，节点+连线，层级标签 |
| Dashboard | `dashboard` | 数字指标、统计汇总、KPI 报表、监控面板 | 大数字卡，图表区，详情列表 |
| Gantt Chart | `gantt` | 项目排期、任务进度、里程碑跟踪 | 横轴时间，横向条形，依赖线 |
| Org Chart | `org-chart` | 团队结构、汇报关系、分类层级 | 树形结构，上下连线，层级缩进 |
| Funnel | `funnel` | 转化率、筛选流程、销售漏斗、用户旅程 | 梯形递减，百分比标注，颜色渐变 |

---

## Auto-Selection Matrix

Content signals → recommended chart type + default style.

| Content Signals (Keywords) | Chart Type | Default Style |
|---------------------------|------------|---------------|
| 步骤、操作、流程、工作流、pipeline、CI/CD、部署 | flowchart | warm |
| 对比、PK、vs、优劣、比较、选型、方案对比 | comparison | minimal |
| 时间、历史、里程碑、路线图、迭代、版本、时间线 | timeline | editorial |
| 系统、服务、架构、组件、拓扑、微服务、网关 | architecture | dark |
| 数字、指标、统计、报表、KPI、监控、数据 | dashboard | glass |
| 计划、排期、进度、甘特、任务、sprint、周期 | gantt | warm |
| 团队、汇报、层级、组织、部门、架构(人员) | org-chart | minimal |
| 转化、漏斗、筛选、销售、留存、用户旅程 | funnel | neon |

**Fallback**: When no signals match, default to `flowchart` + `warm`.

**Multiple signals**: When content matches multiple types, choose the dominant signal. For example, "CI/CD 架构" → prioritize `architecture` over `flowchart` because the architecture keyword signals structural relationships.

---

## Selection Decision Tree

```
User input
  │
  ├─ Contains time/sequence keywords?
  │    ├─ With specific dates/milestones? → timeline
  │    ├─ With task durations/assignments? → gantt
  │    └─ With ordered steps? → flowchart
  │
  ├─ Contains comparison keywords?
  │    └─ Two or more items being compared? → comparison
  │
  ├─ Contains system/component keywords?
  │    ├─ About people/teams? → org-chart
  │    └─ About services/modules? → architecture
  │
  ├─ Contains numeric/metric keywords?
  │    ├─ With conversion/drop-off data? → funnel
  │    └─ Multiple metrics/KPIs? → dashboard
  │
  └─ None of the above → flowchart (default)
```

---

## Chart Type x Style Compatibility

All styles work with all chart types, but some combinations are particularly effective:

| Chart Type | Best Styles | Avoid |
|------------|-------------|-------|
| flowchart | warm, paper, editorial | - |
| comparison | minimal, warm, glass | neon (too busy for comparison) |
| timeline | editorial, warm, paper | - |
| architecture | dark, glass, minimal | paper (too casual) |
| dashboard | glass, dark, neon | paper |
| gantt | warm, minimal, editorial | neon |
| org-chart | minimal, warm, glass | neon |
| funnel | neon, glass, dark | paper, minimal (too flat) |

These are recommendations, not restrictions. User preference always takes priority.

---

## Content Enrichment Guidelines

When user provides minimal input, enrich based on chart type:

| Chart Type | What to Add |
|------------|------------|
| flowchart | Step descriptions, decision points, outcome labels |
| comparison | Pros/cons, scores, recommendation badge |
| timeline | Date formatting, milestone descriptions, era labels |
| architecture | Component roles, protocol labels, data flow direction |
| dashboard | Trend indicators (↑↓), comparison to previous period, status badges |
| gantt | Duration bars, dependency arrows, milestone diamonds |
| org-chart | Role titles, team sizes, responsibility areas |
| funnel | Conversion percentages, drop-off reasons, stage descriptions |
