# Prompt 工程 — Text-to-SQL 的 Prompt 设计

> 在 Prompting 路线下，prompt 的设计直接决定 SQL 生成质量。

## Prompt 结构模板

一个有效的 Text-to-SQL prompt 通常包含以下部分：

```
[System] 你是一个 SQL 专家，根据用户问题和数据库 schema 生成准确的 SQL。
[Schema] 相关表结构和列描述
[业务知识] 指标口径、业务规则
[Few-shot] 相似问题-SQL 样例
[用户问题] 实际问题
[约束] 输出格式、安全规则
```

## 关键技巧

### 1. Schema 表示优化

- 只放相关表（schema linking 筛选后的子集）
- 列描述用自然语言而非纯技术名：`channel_id -- 渠道ID（如 organic/paid/push）`
- 附加主键/外键关系和常用 JOIN 条件

### 2. Few-shot 样例选择

| 策略 | 说明 | 适用场景 |
|---|---|---|
| 随机选择 | 从样例库随机抽取 | 基线 |
| 问题相似度 | 用 embedding 选语义最相近的问题 | 通用场景 |
| SQL 骨架相似度 | 按 SQL 结构模式匹配（DAIL-SQL） | 准确率最高 |
| 业务域分类 | 先分类问题类型，再从对应类型中选 | 业务域明确时 |

### 3. Self-correction

生成 SQL → 执行 → 报错 → 把错误信息拼回 prompt → 重新生成。

关键点：
- 限制重试次数（通常 2-3 次）
- 错误信息要精简，去掉 stack trace，只保留核心报错
- 语法错误恢复率高，语义错误恢复率低

### 4. Chain-of-Thought

引导模型先输出推理过程再生成 SQL，对复杂查询有显著提升。

## 我们的 Prompt 模板方向

1. System prompt 固定：角色 + 安全规则 + 输出格式
2. Schema 动态注入：根据问题类型选择相关表的 DDL + 列描述
3. Few-shot 从范式库检索：按问题语义相似度选 3-5 个最相关的
4. 口径知识：将匹配到的指标口径定义注入
