# 知识库总览

> data-product-workspace 的知识库。系统性原理已迁至外层 [project/](../../)（单一真相源），本目录保留业务独有资产 + 链接索引。

## 知识地图

| 知识域 | 系统性原理（外层 project/） | 本工作区独有资产 |
|--------|---------------------------|------------------|
| ab-testing | [../../ab-testing/](../../ab-testing/) | [./ab-testing/](./ab-testing/)（AB 实验规范、AgentSOP 案例） |
| causal-inference | [../../causal-inference/](../../causal-inference/) | [./causal-inference/](./causal-inference/)（链接索引） |
| agent-llm | [../../agent-llm/](../../agent-llm/) | [./agent-llm/](./agent-llm/)（子 Agent 派单、PM-AI 工作区、数据监控、灰度发布） |
| decision-frameworks | [../../decision-frameworks/](../../decision-frameworks/) | [./decision-frameworks/](./decision-frameworks/)（链接索引） |
| ai-infra | [../../ai-infra-knowledge/](../../ai-infra-knowledge/) | [./ai-infra/](./ai-infra/)（Linux RAG 搭建指南） |
| data-analysis | [../../data-analysis/](../../data-analysis/) | [./data-analysis/](./data-analysis/)（浏览器业务案例、SQL 字典、Kyuubi 优化） |
| product | [../../agent-llm/concepts/](../../agent-llm/concepts/) | [./product/](./product/)（PRD / 竞品 / 用户故事等 Prompt 模板） |

## 业务独有资产（仅本工作区）

| 目录 | 内容 |
|------|------|
| [数据资产/](./数据资产/) | SQL 模板库、指标口径字典、人群包资产登记 |
| [onetrack埋点/](./onetrack埋点/) | 浏览器业务埋点事件字典 |
| [参考资料/](./参考资料/) | 行业报告、文档、白皮书、读书笔记 |
| [方法论/](./方法论/) | 通用工作方法、框架、思路沉淀 |
| [操作手册/](./操作手册/) | 工具配置、操作流程、问题排查 |
| [文档归档/](./文档归档/) | 飞书文档链接、Markdown / HTML 产出归档索引 |

## 组织原则

- 系统性原理（概念 / 方法 / 陷阱 / 案例 / 模板）→ 外层 [project/](../../)
- 业务特定实践资产（SQL 模板、业务案例、埋点字典）→ 本目录
- 每个重复域的 README 是链接索引，指向 project/ 对应目录
