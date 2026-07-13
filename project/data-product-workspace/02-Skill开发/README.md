# 02-Skill 开发

> AI Skill 的规划、设计与索引区。**实际可运行的 Skill/Agent 实现主要在** `01-业务项目/ICE-Data-Workbench-v3/`（`agents/` 与 `skills/`）。本目录侧重规划、方法论与本地开发草稿，子目录当前多为规划占位，随进度逐步填充，避免与 ICE 重复。

## 已有规划文件

| 文件 | 内容 |
|------|------|
| [互联网数据分析Skill体系开发Roadmap.md](./互联网数据分析Skill体系开发Roadmap.md) | 6 大类 Skill 地图与 2 个月落地路线 |
| [规划建议.md](./规划建议.md) | Skill 体系总体框架与交付物定义 |

## 子目录定位与实际实现位置

| 目录 | 定位 | 实际实现 / 关联 |
|------|------|----------------|
| `nl-sql/` | 自然语言取数（Q3 P0 核心） | ICE `agents/data-analysis`、`skills/`；数据资产喂给它 → [数据资产层](../00-知识库/数据资产/) |
| `nl-mapping-table-sql/` | 映射表 SQL | 规划中 |
| `auto-analysis/` | 自动分析 | ICE `agents/biz-insight` |
| `kyuubi/` | Kyuubi 取数能力 | 方法沉淀 → [data-analysis/methods](../00-知识库/data-analysis/methods/) |
| `feishu相关/` | 飞书集成 | 见 feishu CLI 技能 |

## 关联导航

- 数据资产（SQL模板/口径/人群包，服务 nl-sql）→ [../00-知识库/数据资产/](../00-知识库/数据资产/)
- Skill 开发优先级与状态 → [../WORK-PLAN.md](../WORK-PLAN.md)
- ICE 平台实现 → [../01-业务项目/ICE-Data-Workbench-v3/](../01-业务项目/ICE-Data-Workbench-v3/)

> 建立日期：2026-07-01 ｜ 目的：为 Skill 开发区补充导航，说明空壳子目录用途与实际实现位置
