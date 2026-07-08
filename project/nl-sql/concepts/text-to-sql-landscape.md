# Text-to-SQL 技术全景

> 自然语言转 SQL 的主要方法、代表系统与发展脉络。

## 发展阶段

| 阶段 | 时期 | 代表方法 | 特点 |
|---|---|---|---|
| 规则/模板 | ~2017 | 正则匹配、槽填充 | 覆盖窄、需大量人工规则 |
| Seq2Seq | 2017-2020 | SQLNet, SyntaxSQLNet, IRNet | 编码器-解码器，需训练 |
| 预训练模型 | 2020-2023 | BRIDGE, PICARD, RESDSQL | 基于 BERT/T5 微调 |
| LLM Prompting | 2023- | DIN-SQL, DAIL-SQL, C3 | 利用 GPT-4 等闭源模型，prompt 驱动 |
| Multi-Agent | 2024- | MAC-SQL, CHESS | 多角色协作，模块化 |

## 主流 Benchmark

| Benchmark | 规模 | 特点 |
|---|---|---|
| Spider | 10,181 问题 / 200 数据库 | 跨库泛化，最经典 |
| BIRD | 12,751 问题 / 95 数据库 | 更贴近真实，含业务知识 |
| WikiSQL | 80,654 问题 / 24,241 表 | 单表简单查询 |
| KaggleDBQA | 272 问题 / 8 数据库 | 真实 Kaggle 数据集 |

## 当前 SOTA 表现

在 BIRD benchmark（2024）上，最佳方法的执行准确率约 72%，说明复杂真实场景仍有很大提升空间。业务特定场景通过范式库 + 口径知识可以大幅超越通用基准。

## 对我们的启示

- 通用 benchmark 的难度远超我们的业务场景（我们表少、查询模式集中）
- 关键不是追求通用 SOTA，而是在业务域内做到极高准确率
- 范式库 + few-shot 选择是性价比最高的路线
