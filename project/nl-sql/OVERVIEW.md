# NL-SQL (Text-to-SQL) 领域全景

> 本文梳理自然语言转 SQL 的技术全景、核心挑战和研究方向，为 Q3 nl-sql 建设提供方法论指引。

## 一、问题定义

Text-to-SQL 是将用户的自然语言问题转化为可执行 SQL 查询的任务。典型流程：

```
用户问题 → 意图理解 → Schema Linking → SQL 生成 → 执行验证 → 结果返回
```

## 二、核心挑战

| 挑战 | 说明 | 我们的现状 |
|---|---|---|
| Schema 规模 | 表/列数量大时 LLM 上下文不够或噪音多 | 内容生态涉及数十张表，需做 schema 筛选 |
| 业务语义映射 | "有效 DAU" → 具体口径和字段的映射 | 已有指标口径字典，需结构化喂给模型 |
| 复杂查询 | 多表 JOIN、嵌套子查询、窗口函数 | 当前准确率瓶颈，需拆解策略 |
| 歧义消解 | 同一词在不同业务场景含义不同 | 需多轮对话澄清 |
| 安全性 | 防止生成破坏性 SQL（DELETE/DROP） | SQL 审计已有基础设施 |

## 三、技术路线分类

### 3.1 Prompting 路线（当前主力）

通过精心设计 prompt + few-shot 样例驱动 LLM 直接生成 SQL。

- **优点**：迭代快、无需训练、可利用最强闭源模型
- **缺点**：依赖 prompt 质量和样例选择
- **关键技术**：schema 表示、few-shot selection、self-correction

### 3.2 Fine-tuning 路线

在开源模型上用 (NL, SQL) 对进行微调。

- **优点**：可针对业务域深度优化
- **缺点**：需要标注数据、模型更新成本高
- **代表**：SQLCoder、NSQL、CodeS

### 3.3 Agent 路线（趋势方向）

多 Agent 协作：planner 拆解问题、retriever 检索 schema/样例、generator 生成 SQL、verifier 验证执行。

- **优点**：模块化、可组合、可观测
- **缺点**：延迟高、调试复杂
- **代表**：MAC-SQL、DIN-SQL、CHESS

## 四、我们的技术选择

基于团队现状（2 人、Q3 时间窗口），采用 **Prompting + RAG 增强** 路线：

1. **Schema 压缩**：按业务域预筛选相关表/列，减少上下文噪音
2. **范式库驱动 few-shot**：用真实业务 SQL 模板作为 few-shot，按语义相似度检索
3. **口径知识注入**：将指标口径字典作为 system prompt 的一部分
4. **自修正**：生成 SQL → 试执行 → 报错则带错误信息重新生成
5. **渐进覆盖**：从高频简单查询开始，逐步扩展复杂场景

## 五、评估框架

| 指标 | 定义 | 目标 |
|---|---|---|
| 执行准确率 (EX) | 生成 SQL 执行结果与标准答案一致 | 80%+ (7月底)，90%+ (Q3末) |
| 覆盖率 | 能处理的查询类型占日常取数需求比例 | 80% |
| 首次成功率 | 无需人工修正即可使用 | 追踪但不设硬目标 |
| 平均延迟 | 从提问到返回结果的时间 | < 30s |

## 六、学习路线图

1. ✅ 理解 Text-to-SQL 全景（本文）
2. 🔲 Schema Linking 原理与实践 → `concepts/schema-linking.md`
3. 🔲 Prompt 工程方法 → `methods/prompt-engineering.md`
4. 🔲 RAG 增强取数 → `methods/rag-for-sql.md`
5. 🔲 范式库设计 → `patterns/pattern-library-design.md`
6. 🔲 评估与 Badcase 分析 → `evaluation/`
