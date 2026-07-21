# 知识库总览

> 系统化沉淀数据产品、AI、数据分析的方法论、工具和经验。遵循「OVERVIEW导读 + README索引 + 概念-方法-陷阱-案例-模板」五维度组织原则。

## 📖 阅读指南

每个知识域采用**双入口**设计：
- **OVERVIEW.md**：开篇导读，教学入口，先读这个。用通俗语言讲清楚「这个领域解决什么问题、不解决什么问题、核心心智模型是什么、常见坑有哪些、学习路径是什么」，最后给心法和Checklist。
- **README.md**：导航索引，研究范围、目录结构、文件清单、跨域关联。需要查具体内容时读这个。

**阅读顺序建议**：先读对应知识域的 OVERVIEW.md 建立心智模型，再按需深入具体文件。

## 🗺️ 知识地图

| 知识域 | OVERVIEW导读 | 核心内容 |
|--------|---------------|----------|
| [ab-testing/](./ab-testing/) | ✅ [OVERVIEW.md](./ab-testing/OVERVIEW.md) | AB测试方法论 | 假设检验、样本量计算、CUPED、序贯检验、分流策略、业界实践 |
| [causal-inference/](./causal-inference/) | ✅ [OVERVIEW.md](./causal-inference/OVERVIEW.md) | 因果推断 | DID、DML、工具变量、合成控制、uplift建模、倾向得分匹配 |
| [agent-llm/](./agent-llm/) | ✅ [OVERVIEW.md](./agent-llm/OVERVIEW.md) | Agent与LLM | Transformer原理、Agent架构、RAG、MCP、提示工程、工程化落地 |
| [decision-frameworks/](./decision-frameworks/) | ✅ [OVERVIEW.md](./decision-frameworks/OVERVIEW.md) | 决策框架 | 第一性原理、OODA、RICE、SWOT、系统思维、AI决策框架 |
| [data-analysis/](./data-analysis/) | ✅ [OVERVIEW.md](./data-analysis/OVERVIEW.md) | 数据分析 | SQL最佳实践、Python分析、分析方法论、指标体系、案例沉淀 |
| [数据资产/](./数据资产/) | 服务 nl-sql | 数据资产层 | SQL模板库、指标口径字典、人群包资产登记 |
| [product/](./product/) | ✅ [OVERVIEW.md](./product/OVERVIEW.md) | 产品方法论 | 增长、指标体系、需求管理、运营、PRD撰写、AI产品 |
| [ai-infra/](./ai-infra/) | ✅ [OVERVIEW.md](./ai-infra/OVERVIEW.md) | AI基础设施 | 训练优化、推理服务、MLOps平台、RAG部署、成本/延迟优化 |
| [参考资料/](./参考资料/) | - | 外部资料 | 行业报告、文档、白皮书、读书笔记 |
| [方法论/](./方法论/) | - | 通用方法论 | 工作方法、框架、思路沉淀 |
| [操作手册/](./操作手册/) | - | 工具使用指南 | 工具配置、操作流程、问题排查 |
| [合作方/](./合作方/) | - | 合作方沟通记录 | 按人记录沟通历史、待办事项、约定事项，持续更新 |
| [文档归档/](./文档归档/) | - | 文档统一归档 | 飞书文档链接、Markdown/HTML等各类产出文档归档索引 |

> **完善度说明**：各知识域充实度不一——ab-testing / agent-llm / decision-frameworks / data-analysis / 数据资产 内容较充实；causal-inference / product / ai-infra 的部分维度（cases / pitfalls / templates 等）为规划骨架、待按需填充。空目录代表"预留待填"，非遗漏。

## 📂 统一组织原则

每个知识域遵循统一的目录结构（允许根据领域特点灵活扩展子目录）：

```
知识域/
├── OVERVIEW.md    # 开篇导读（教学入口，先读这个）
├── README.md      # 导航索引 + 研究范围
├── concepts/      # 核心概念、理论基础、定义
├── methods/       # 方法论、落地步骤、工具使用
├── pitfalls/      # 踩坑记录、常见陷阱、失败模式
├── cases/         # 行业案例、实战经验、业务落地
├── templates/     # 可复用模板、Checklist（可选）
├── tools/         # 工具使用、代码模板（可选）
└── papers/        # 论文、深度资料（可选）
```

## 📝 贡献规则

1. **新增内容先找对分类**：判断内容属于哪个知识域，放到对应子目录
2. **文件命名清晰**：使用`中文标题.md`便于检索，避免无意义英文缩写
3. **引用标注来源**：所有外部引用的数据、观点必须标注来源和时间
4. **标注推断**：无数据支撑的个人判断必须明确标注「推断」
5. **跨域关联**：相关内容在README中建立链接，形成知识网络
6. **OVERVIEW先行**：新领域先写OVERVIEW.md建立心智模型，再填充细节内容

## 🚀 快速导航

- 第一次进知识库 → 先读每个域的 **OVERVIEW.md** 建立整体认知
- 日常数据分析参考 → `data-analysis/`
- AB实验分析参考 → `ab-testing/`
- 因果推断/观察性研究 → `causal-inference/`
- Agent/Skill开发参考 → `agent-llm/`
- 做决策/优先级排序 → `decision-frameworks/`
- 产品方法论参考 → `product/`
- AI基础设施/模型部署 → `ai-infra/`
- 工具配置问题排查 → `操作手册/`
- 历史产出文档查找 → `文档归档/`
