# nl-sql — 自然语言取数（Text-to-SQL）方法论

> Q3 一号位核心场景：打透自然语言取数，覆盖 80% 日常取数需求，准确率 90%+。
> 本目录沉淀 Text-to-SQL 的系统性原理与方法论；实操案例和数据资产在 [data-product-workspace/00-知识库/数据资产/](../data-product-workspace/00-知识库/数据资产/)。

## 目录结构

```
nl-sql/
├── README.md               # 本文件
├── OVERVIEW.md              # 领域全景与研究路线图
├── concepts/                # 基础概念
│   ├── text-to-sql-landscape.md   # Text-to-SQL 技术全景
│   ├── schema-linking.md          # Schema Linking（表/列匹配）
│   └── query-decomposition.md     # 复杂查询拆解策略
├── methods/                 # 核心方法
│   ├── prompt-engineering.md      # Prompt 工程（few-shot / CoT / self-correction）
│   ├── schema-representation.md   # Schema 表示与压缩
│   ├── rag-for-sql.md             # RAG 增强取数（检索相似 SQL / 业务知识）
│   ├── error-recovery.md          # 错误恢复与自修正
│   └── multi-turn.md              # 多轮对话取数
├── evaluation/              # 评估体系
│   ├── metrics.md                 # 评估指标（执行准确率 / 逻辑准确率 / 覆盖率）
│   └── badcase-analysis.md        # Badcase 分析方法论
└── patterns/                # 业务查询范式
    ├── pattern-library-design.md  # 范式库设计原则
    └── few-shot-selection.md      # Few-shot 样例选择策略
```

## 与其他目录的分工

| 我想查什么 | 去哪里 |
|---|---|
| Text-to-SQL 原理、方法论、学术进展 | **本目录** |
| SQL 模板库、指标口径字典、范式库实战 case | [data-product-workspace/00-知识库/数据资产/](../data-product-workspace/00-知识库/数据资产/) |
| NL-SQL Skill 使用案例 | [knowledge-base/AI-SKILL/](../../knowledge-base/AI-SKILL/) |
| LLM/Agent 通用原理 | [agent-llm/](../agent-llm/) |
| Q3 OKR 与规划 | [data-product-workspace/DECISIONS.md](../data-product-workspace/DECISIONS.md) |

## 参考论文与资源

> 逐步补充，按影响力排序。

| 论文/资源 | 关键贡献 |
|---|---|
| Spider / BIRD benchmark | Text-to-SQL 主流评测基准 |
| DIN-SQL (2023) | 分解-推理-自修正 pipeline |
| DAIL-SQL (2024) | 基于相似度的 few-shot 选择 |
| C3 (2023) | 清晰-简洁-正确 prompting 框架 |
| MAC-SQL (2024) | 多 Agent 协作生成 SQL |
| CHESS (2024) | 上下文增强的 Schema 筛选 |
