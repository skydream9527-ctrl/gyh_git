# knowledge-base — AI/数据 实践记录与调优日志

> **定位**：这里存放 **实践记录、调优日志、规划文档**（工程笔记式）。
> 与 [project/](../project/) 的分工：`project/` 是**系统性原理/方法论**（教科书式，每个领域有 README/OVERVIEW/READING-MAP），本目录是**实操中沉淀的记录**。两者**互补，不重复**。

## 与 project/ 怎么分工

| 我想查什么 | 去哪里 |
|---|---|
| Agent/RAG/Skill 的原理、架构、方法论 | [project/agent-llm/](../project/agent-llm/)（advanced-rag / retrieval-basics / agent-loop-architectures …） |
| Agent 效果评估的实操记录、调优过程 | 本目录 [AI-Agent/](AI-Agent/) |
| RAG 调优记录、mify 对接、埋点指标 | 本目录 [RAG/](RAG/) |
| 埋点设计原理、命名规范 | [project/event-tracking/](../project/event-tracking/) |
| 埋点 FAQ、排障、变更记录 | 本目录 [数据埋点/](数据埋点/) |
| 数据分析方法论 | [project/data-analysis/](../project/data-analysis/) |
| 数据治理、质量监控、安全合规 | 本目录 [数据治理/](数据治理/) |

## 子目录索引

| 目录 | 内容 |
|---|---|
| [AI-Agent/](AI-Agent/) | Agent 效果评估与迭代记录、Agent 文档库、Agent 配置与编排 |
| [AI-SKILL/](AI-SKILL/) | Skill 使用案例库、Skill 开发规范与模板、Skill 文档库 |
| [RAG/](RAG/) | RAG 调优记录、参考文档、埋点指标、对接 mify 平台、规范 |
| [数据埋点/](数据埋点/) | 埋点 FAQ 与排障手册、变更记录、方案文档库、验收测试 |
| [数据治理/](数据治理/) | 数据路径与指标定义、数据安全合规、数据质量监控规则 |
| [技术沉淀/](技术沉淀/) | 内部技术沉淀（AI-Native / 数据分析 / 看板播报 / 经营预测）+ 外部部门产出 |
| [导航/](导航/) | 全局知识地图、新人 Onboarding 指南、机器人使用指南 |
| [standalone/](standalone/) | 信息流参数知识库、重要参数明细枚举 |

## 维护约定

- 实操中产生的调优记录、踩坑日志、规划文档 → 放本目录对应主题
- 系统性整理成原理/方法论 → 放 [project/](../project/) 对应领域
- 同一主题在两处都有时：本目录记"我做过什么、踩了什么坑"，project/ 记"它是什么、怎么用"
