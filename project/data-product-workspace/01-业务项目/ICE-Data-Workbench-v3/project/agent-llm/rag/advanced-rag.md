# Advanced RAG：Self-RAG / CRAG / GraphRAG

> [retrieval-basics.md](retrieval-basics.md) 讲了 RAG 的"骨架"。本文是"花活"——当朴素 RAG 在你的场景上吃瘪时，业界这两年涌现了几种更聪明的范式。本文系统讲清 **Self-RAG / CRAG / GraphRAG / Adaptive RAG** 的机制、适用场景、工程权衡。

---

## 一、为什么需要 Advanced RAG

朴素 RAG 的短板（详见 [retrieval-basics.md](retrieval-basics.md) 第 11 节）：

| 朴素 RAG 失败的场景 | 根本原因 |
|---|---|
| 答案需要跨多个文档拼接 | 单次检索召回的片段彼此独立 |
| 检索不到相关内容时仍然胡编 | 没有"召回质量评估" |
| 回答需要全局视角（"这本书的核心论点是？"） | 局部 chunk 看不到全局 |
| 检索召回了无关 / 错误片段 | 没有"过滤错误信息"机制 |
| 用户问题模糊 / 多意图 | 单次检索不能动态决策 |

→ Advanced RAG 不是"一种方法"，是一组针对不同失败模式的修补。

---

## 二、Self-RAG：让模型决定要不要 / 怎么 / 用不用检索

**Self-RAG**（Asai et al., 2023）的核心思想：不是每次都检索，而是让 LLM **自己判断**当前问题需不需要检索、检索回的内容好不好用、最终答案靠不靠谱。

### 关键创新：Reflection Tokens

模型在生成过程中可以输出特殊 token 表达"反思"：

```
[Retrieve]   ：要不要检索？（Yes / No / Continue）
[IsRel]      ：这个检索片段相关吗？（Relevant / Irrelevant）
[IsSup]      ：我的回答有这个片段支撑吗？（Fully / Partially / No）
[IsUse]      ：整体回答有用吗？（5 / 4 / 3 / 2 / 1）
```

### 工作流

```
用户问题 → LLM 决定 [Retrieve?]
                ┌────┴────┐
              是          否
                │          │
                ▼          ▼
            检索 top-K    直接回答
                │
                ▼
       并行处理每个片段：
         - [IsRel] 评估相关性
         - 用片段生成回答
         - [IsSup] 评估"答案有支撑吗"
                │
                ▼
       选择"最有用 + 最有支撑"的回答输出
```

### 优势 vs 代价

| 优势 | 代价 |
|---|---|
| 减少不必要的检索 | 模型必须在 SFT 阶段被训过 reflection tokens |
| 检测并跳过无关片段 | 推理成本 1.5-3× |
| 答案可解释（能看到 reflection） | 实现复杂 |

工程实现：通常要 fine-tune 一个专门的 Self-RAG 模型，或在 prompt 里模拟 reflection 流程（功能更弱但可用）。

---

## 三、CRAG（Corrective RAG）：召回质量自评 + 兜底

**CRAG**（Yan et al., 2024）解决的痛点：检索召回的内容**未必相关**——朴素 RAG 不管对错都塞给 LLM，导致幻觉或错答。

### 工作流

```
用户问题 → 标准检索 top-K
              │
              ▼
       Retrieval Evaluator（小模型）打分：
         Correct（相关）/ Ambiguous（模糊）/ Incorrect（不相关）
              │
       ┌──────┼──────┐
    Correct  Ambiguous  Incorrect
       │       │           │
       ▼       ▼           ▼
   直接用   用 + 兜底     完全用兜底
            （Web 搜索）  （Web 搜索）
              │
              ▼
       去噪：把检索文档拆成"知识片段"，
            过滤无关，重组成 refined context
              │
              ▼
       LLM 基于 refined context 回答
```

### 关键组件

1. **Retrieval Evaluator**：训一个轻量分类器（T5-small 量级）判断 (query, doc) 相关度
2. **Web 搜索作为兜底**：当本地知识库不够，用 Web search（Bing / Tavily / Brave）
3. **去噪重组**：不是整段塞进去，而是抽取 atomic 知识片段，过滤后重组

### 优势

- **召回质量可控**：错误 / 无关片段不会污染回答
- **覆盖外延扩展**：本地知识库 + Web 搜索 hybrid

### 代价

- 需要训 retrieval evaluator
- 调用 Web 搜索增加延迟和成本

---

## 四、GraphRAG：用知识图谱解决"全局问题"

**GraphRAG**（Microsoft Research, 2024）解决朴素 RAG 完全无解的问题：**全局型问题**。

### 朴素 RAG 解不了的问题

```
Q：在这本书里，哪几个角色之间的关系最重要？
Q：这家公司过去三年的战略主线是什么？
Q：这套代码库的核心架构思想是？

→ 这些问题的答案不在任何一个 chunk 里
→ 需要把分散的信息"汇总成全局视角"
```

朴素 RAG 检索 top-K 个 chunk，每个 chunk 都是局部——天然无法回答全局问题。

### GraphRAG 的核心思路

```
离线阶段：
  1. 文档 → LLM 抽取实体（人、地、事、概念）
  2. LLM 抽取实体之间的关系
  3. 构建知识图谱
  4. 在图上做社区检测（community detection），切成"主题群"
  5. 对每个社区生成 community summary（用 LLM 总结）

在线阶段：
  Local 查询：用图 + chunk 检索（类似传统 RAG）
  Global 查询：
    - 让每个 community summary 各自尝试回答
    - 把这些 partial answer 再聚合成最终答案 (map-reduce 风格)
```

### 工作流（Global Query 模式）

```
用户问题（全局型）
   │
   ▼
所有 community summaries 并行处理：
   每个 summary → LLM 用它产出 "局部答案 + 相关度评分"
   │
   ▼
按相关度排序，取 top-N
   │
   ▼
LLM 把 top-N 局部答案聚合成最终答案
```

### 优势

- **全局问题**能答（之前是 RAG 死角）
- 知识图谱可解释、可审计
- 一次构建，多次复用

### 代价

- **离线构建成本极高**：每篇文档要 LLM 抽实体、关系、再社区检测、再做总结——10K 文档可能要几十美元 LLM 调用
- 实体抽取质量决定一切——schema 设计是关键
- 不适合频繁更新的知识库

### 实操工具

- Microsoft GraphRAG 开源库：https://github.com/microsoft/graphrag
- LightGraphRAG（轻量替代）
- LangChain GraphRAG 集成

---

## 五、Adaptive RAG：路由不同复杂度的 query

朴素 RAG **不管什么问题都走一样的流程**——但不同问题该走不同路径：

```
"巴黎在哪个国家"             → 不需要 RAG，直接答
"我们公司去年财报怎么样"      → 单次检索 + 回答
"对比 A、B、C 三家公司近三年战略"  → 多次检索 + 综合
"这本书的核心论点是？"        → GraphRAG / 全局模式
```

**Adaptive RAG**（Jeong et al., 2024）的思路：训一个轻量分类器（或用 LLM 判断）把 query 路由到不同复杂度的 RAG 流程。

```
Query → Complexity Classifier
              ┌─────┼─────┬─────┐
            A 类   B 类  C 类  D 类
              │      │     │     │
              ▼      ▼     ▼     ▼
            直接答 单次  多步  GraphRAG
                  RAG   RAG
```

实操：

- 简单实现：用 LLM 直接判断 "需要 RAG 吗 / 需要多次检索吗"
- 高级实现：用小模型（DistilBERT）训分类器

### 优势 vs 代价

- ✅ 复杂查询也能处理
- ✅ 简单查询不浪费成本
- ❌ 路由错了影响体验
- ❌ 流程多 → 维护复杂度上升

---

## 六、Iterative / Multi-hop RAG：多步检索

某些问题一次检索不够——需要先检索一部分，根据结果继续检索：

```
Q：钱学森的博士生导师的导师在 1960 年代的研究方向？

Step 1：检索 "钱学森博士导师"
  → 召回："钱学森博士导师是冯·卡门"
  
Step 2：基于 Step 1 结果检索 "冯·卡门的博士导师"
  → 召回："冯·卡门博士导师是普朗特"
  
Step 3：基于 Step 2 结果检索 "普朗特 1960 年代研究方向"
  → 召回："普朗特已 1953 年去世"
  
Step 4：综合给出最终答案
```

代表方法：

- **IRCoT**（Trivedi et al., 2023）：CoT + 每步可触发检索
- **FLARE**（Jiang et al., 2023）：模型生成时低置信度 token 触发检索
- **ReAct + RAG**（详见 [../agents/react-and-variants.md](../agents/react-and-variants.md)）：把检索当 tool

### 何时必要

- 多跳推理任务（HotpotQA 类问题）
- 知识需要"沿路径深挖"

### 何时不必要

- 单跳问题 → 增加成本无益
- 用户不耐烦等多次检索的延迟

---

## 七、HyDE（Hypothetical Document Embedding）回顾 + 进化

[retrieval-basics.md](retrieval-basics.md) 第 7 节讲过 HyDE：让 LLM 假装写一段答案，用这段答案的 embedding 检索。

### 进化：Step-back Prompting

不是写假答案，而是**先从问题中归纳出"高层概念"再检索**：

```
原问题：用户支付订单 #12345 时显示"渠道异常"是什么原因？

Step-back: 支付系统的渠道异常通常由哪些原因造成？
   ↓
按 step-back 检索 → 召回支付架构 / 渠道异常类型文档
   ↓
基于这些 + 原问题给出具体诊断
```

适合：技术诊断 / 复杂业务问题。

---

## 八、决策树：我该用哪个 Advanced RAG

```
                你最大的痛点是？
       ┌────────┬──────┬──────┬─────────┐
   召回质量差  全局问题  多跳推理  query 复杂度多样
       │        │        │           │
       ▼        ▼        ▼           ▼
     CRAG  GraphRAG  IRCoT/FLARE  Adaptive
            │
        预算够 + 静态文档？
        ┌────┴────┐
       是          否
        │          │
        ▼          ▼
     GraphRAG   先做 LightRAG 再升级

如果以上都需要 → 用 Self-RAG 框架，因为它的 reflection 机制能动态决策
```

---

## 九、生产工程的"组合套餐"

业界头部 RAG 系统通常**多种组合**：

```
1. Indexing 阶段：
   - 结构化分块（heading / code / table）
   - Late Chunking（如果支持）
   - 抽实体 + 构建轻量知识图谱（混合 GraphRAG 思想）

2. Retrieval 阶段：
   - Adaptive 路由（按 query 复杂度）
   - Hybrid Retrieval（dense + BM25）
   - HyDE / Step-back / Multi-Query 改写
   - Reranker

3. Generation 阶段：
   - Self-RAG / CRAG 风格的相关度评估
   - 多文档融合时 Map-Reduce 聚合
   - 必带 citation
   
4. 多步任务：
   - 把 RAG 当 tool，套在 ReAct Agent 里（详见 [react-and-variants](../agents/react-and-variants.md)）
```

效果：相比朴素 RAG，**召回精度 + 答案准确率提升 50-200%**。

---

## 十、几个反直觉的发现

### 1. "更复杂的 RAG 不一定更好"
- 朴素 RAG + 好的分块 + 好的 reranker 经常打败花哨的 Advanced RAG
- 先把 basics 做扎实，再上 advanced

### 2. "GraphRAG 在小知识库上反而退化"
- 抽实体的 LLM 调用对小库性价比极差
- 知识库 < 1MB 文本时直接长 context 最划算

### 3. "Self-RAG 的 reflection token 经常被忽略"
- 没 fine-tune 过的模型用 prompt 模拟 reflection 效果差很多
- 真要上 Self-RAG，准备好训 / 微调成本

### 4. "Adaptive 路由错了比不路由更糟"
- 简单问题被路到 GraphRAG → 慢且不一定准
- 复杂问题被路到直接答 → 完全错
- 路由分类器的精度本身要 > 90% 才值得

### 5. "Long context 替代不了 RAG，但能简化 RAG"
- 100K-1M context 让"中等知识库直接全塞"成为可能
- 但成本和延迟仍劝退大规模应用
- **RAG 与 long context 是互补不是替代**

---

## 十一、评测的特殊考量

Advanced RAG 的评测维度比朴素 RAG 多：

```
基础维度（详见 [retrieval-basics.md](retrieval-basics.md)）：
   Recall@K、MRR、Faithfulness、Answer Relevance

新增维度：
   - 路由准确率（Adaptive RAG）
   - 多跳推理成功率（Multi-hop）
   - Web fallback 触发恰当率（CRAG）
   - 全局问题回答覆盖度（GraphRAG）
   - Reflection 决策合理性（Self-RAG）
   - 总成本（advanced 方法成本飙升 2-10×，必须监控）
```

→ 详见 [../evaluation/llm-as-judge.md](../evaluation/llm-as-judge.md)

---

## 十二、Checklist

```
□ 1. 朴素 RAG 的 basics（分块、hybrid、rerank）做扎实了吗？
□ 2. 我的痛点和 Advanced RAG 解决的痛点对得上吗？
□ 3. 离线构建成本（特别 GraphRAG）能接受？
□ 4. 在线延迟可接受（Self-RAG / Multi-hop 慢）？
□ 5. 评测维度覆盖了 advanced 特有的失败模式？
□ 6. 有降级方案（advanced fail 时退到 basic RAG）？
□ 7. 知识库更新频率和方法的"重建成本"匹配吗？
□ 8. 总 token 成本 vs 收益值得吗？
```

---

## 十三、扩展阅读

- 本目录：[retrieval-basics.md](retrieval-basics.md)
- 相关：[../agents/react-and-variants.md](../agents/react-and-variants.md)、[../evaluation/llm-as-judge.md](../evaluation/llm-as-judge.md)
- Asai et al. (2023) — *Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection*
- Yan et al. (2024) — *Corrective Retrieval Augmented Generation*
- Edge et al. (2024) — *From Local to Global: A Graph RAG Approach to Query-Focused Summarization*（Microsoft GraphRAG）
- Jeong et al. (2024) — *Adaptive-RAG: Learning to Adapt Retrieval-Augmented Large Language Models through Question Complexity*
- Trivedi et al. (2023) — *Interleaving Retrieval with Chain-of-Thought Reasoning for Knowledge-Intensive Multi-Step Questions*（IRCoT）
- Jiang et al. (2023) — *Active Retrieval Augmented Generation*（FLARE）
- Microsoft GraphRAG: https://github.com/microsoft/graphrag
- LangChain Advanced RAG cookbook
- 本仓库 [knowledge-base/RAG/](../../../knowledge-base/RAG/)
