# knowledge-base — AI/数据 实践记录与调优日志

> **定位**：实践记录、调优日志、规划文档（工程笔记式）。
> 与 [project/](../project/) 分工：`project/` = 系统性原理 / 方法论（教科书式）；本目录 = 实操中沉淀的记录。互补不重复。

## 与 project/ 怎么分工

| 我想查什么 | 去哪里 |
|---|---|
| Agent/RAG/Skill 原理、架构、方法论 | [project/agent-llm/](../project/agent-llm/) |
| Agent 效果评估实操记录、智能体层规划 | [AI-Agent/](AI-Agent/) |
| RAG 调优、mify 对接、rag-web-ui 教程 | [RAG/](RAG/) |
| 埋点设计原理、命名规范 | [project/event-tracking/](../project/event-tracking/) |
| 埋点业务方案（v10.4 等） | [数据埋点/](数据埋点/) |
| 数据分析方法论 | [project/data-analysis/](../project/data-analysis/) |
| 数据治理、质量监控（飞书源文档） | [feishu-source-links.md](feishu-source-links.md) |

## 子目录索引

| 目录 | 内容 |
|---|---|
| [AI-Agent/](AI-Agent/) | Agent 智能体层规划、配置与编排文档 |
| [AI-SKILL/](AI-SKILL/) | Skill 使用案例库（Confidence-Detection / Data-Tracking-Plan / Feed-Release-AB / NL-SQL / NL-Billboard 等）+ 开发规范 + 文档库 |
| [RAG/](RAG/) | RAG 知识库层规划、rag-web-ui 教程、对接 mify 平台 |
| [数据埋点/](数据埋点/) | v10.4 内容中心图文沉浸式场景埋点方案（业务特定） |
| [技术沉淀/](技术沉淀/) | 内部沉淀（数据智能体系规划 / 工具选型 / 看板播报 / PUSH 分析）+ 外部部门产出（AI-Native 协作 / 字节激励调研） |
| [standalone/](standalone/) | 重要参数明细枚举知识库 |
| [feishu-source-links.md](feishu-source-links.md) | 飞书源文档链接索引（电子表格 / 多维表格 / wiki 子页面无法导出 Markdown 的占位汇总） |

> 导航/、数据治理/ 下的纯链接占位文件已清理，原始飞书链接统一收录在 [feishu-source-links.md](feishu-source-links.md)。

## 维护约定

- 实操中产生的调优记录、踩坑日志、规划文档 → 放本目录对应主题
- 系统性整理成原理 / 方法论 → 放 [project/](../project/) 对应领域
- 同一主题在两处都有时：本目录记"我做过什么、踩了什么坑"，project/ 记"它是什么、怎么用"
- 飞书电子表格 / 多维表格类内容无法导出 Markdown，只在 [feishu-source-links.md](feishu-source-links.md) 登记链接
