# Agent 记忆系统

> 让 Agent "**记住**" 是从原型到产品最大的鸿沟之一。本文系统讲清记忆的分类（短期/长期、Episodic/Semantic/Procedural）、工程实现（窗口/摘要/向量/图）、以及生产环境的取舍。

---

## 一、为什么记忆是 Agent 的核心难题

LLM 本身是**无状态**的——每次调用都是从零开始。让 Agent 像人一样跨会话保留信息，技术栈要解决：

- 一次对话内**不被上下文窗口卡住**
- 跨对话记住用户偏好、过去的事实、犯过的错
- 检索时**精准、不引入无关信息**
- 写入时**不让旧信息污染新观点**

业界目前没有银弹方案，但有一套成熟的工程模式。

---

## 二、记忆的两个维度

### 维度 1：时间尺度

```
短期记忆（Short-term Memory）
  范围：当前会话内
  存储：上下文窗口
  特点：随会话结束消失

长期记忆（Long-term Memory）
  范围：跨会话、跨用户、跨周期
  存储：外部数据库（向量库 / 关系库 / 图库）
  特点：需要主动写入和检索
```

### 维度 2：内容类型（借鉴认知科学）

```
Episodic 情景记忆 — "发生了什么"
  例：用户上周问过我什么、Agent 上次跑工具失败的细节

Semantic 语义记忆 — "我知道什么"
  例：用户的角色是产品经理、产品 KPI 是 DAU

Procedural 程序记忆 — "怎么做"
  例：发周报的固定流程、查指标的 SQL 模板
```

> 这三种记忆在工程上对应**不同的存储策略和检索方式**，一锅端会让系统又慢又乱。

---

## 三、短期记忆的三种工程实现

### 1. 朴素窗口（Sliding Window）

```python
messages = messages[-N:]  # 只保留最近 N 条
```

| 优势 | 劣势 |
|---|---|
| 简单 | 重要早期信息被丢 |
| 成本可控 | 长任务必崩 |

适合：简单 Q&A、客服一问一答。

### 2. 摘要 + 滑窗（Summary + Window）

```python
if len(messages) > THRESHOLD:
    summary = llm_summarize(messages[:-K])
    messages = [{"role": "system", "content": summary}] + messages[-K:]
```

经典做法。LangChain 的 `ConversationSummaryBufferMemory` 就是这个。

| 优势 | 劣势 |
|---|---|
| 节省 token，保留早期要点 | 摘要丢细节 |
| 实现成本低 | 多轮摘要会"摘要漂移"（信息逐步失真） |

### 3. Hierarchical Memory（分级摘要）

```
原始消息 →（每 5 条）→ 微摘要 →（每 20 条）→ 大摘要 → ...
```

参考 OpenAI ChatGPT 的"Memories"特性、MemGPT 的设计思想。

```
当前对话窗口（最详细）
   ↓
近期摘要（中等粒度）
   ↓
长期摘要（极简、关键事实）
```

适合：长会话型 Agent（写作助手、研究 Agent、Coding Agent）。

---

## 四、长期记忆：四种存储模式

### 1. Vector Memory（向量记忆，最常用）

```
用户消息 / 关键事实 → embedding → 写入向量库
查询时：当前 query → embedding → 相似度检索 → 注入 prompt
```

**优势**：语义检索、扩展性强、技术栈成熟

**劣势**：
- 召回不可控（"上周说过的"未必能召回）
- 难以表达**关系**（A 和 B 的关系）
- 重复 / 矛盾信息互相干扰

工具：Pinecone、Weaviate、Qdrant、Chroma、PG Vector、Milvus。

### 2. Key-Value / 结构化（Profile Memory）

```
{
  "user_id": "U123",
  "name": "李四",
  "role": "产品经理",
  "interests": ["AB 测试", "因果推断"],
  "communication_style": "先结论后细节"
}
```

适合：用户画像、偏好、固定属性。

| 优势 | 劣势 |
|---|---|
| 100% 可控、可审查 | 写入要 schema 设计 |
| 检索快 | 不灵活，schema 演化难 |

→ 这个工作区的 [USER.md](../../../USER.md) 就是典型的"用户 profile 记忆"。

### 3. Graph Memory（图记忆）

```
节点：实体（人、项目、概念）
边：  关系（属于、依赖、引用）

例：
  [李四 PM] --[负责]--> [浏览器项目]
  [浏览器项目] --[包含]--> [发现频道]
  [发现频道] --[使用]--> [X 推荐算法]
```

适合：知识网络、长期的人 / 物 / 概念关系。

工具：Neo4j、Memgraph、LangChain GraphRAG。

> 但**实现成本高**——只在记忆量极大且关系复杂时才用。多数应用从向量 + KV 起步。

### 4. Hybrid（事实主流）

生产 Agent 通常**几种混用**：

```
Profile Memory   →  存稳定的用户画像（KV）
Episodic Memory  →  存历史事件（向量库 + 时间戳）
Semantic Memory  →  存习得的事实（向量库 / KV）
Procedural Memory→  存模板和工作流（KV）
```

→ ChatGPT Memory、Claude Projects、Cursor Memory、本工作区的"AI 自动维护 MEMORY.md"等都是 Hybrid。

---

## 五、记忆写入的"两个最大坑"

### 1. 无差别写入 → 噪音爆炸

不能"什么都往 memory 塞"。必须**有写入策略**：

```
触发条件：
  - 用户明确说"记住这个"
  - 表达偏好（"我喜欢..."、"以后..."）
  - 关键决策（决定 / 选择某方案）
  - 校正（"不对，应该..."）
  - 错误教训（Agent 失败的反思）

不写入：
  - 闲聊
  - 一次性查询的内容
  - 临时数据
```

> **写入门槛宁高勿低**。多数失败的"AI 助手"不是因为记不住，是记了太多噪音。

### 2. 没有去重 / 更新 / 遗忘机制

时间一久 memory 里全是矛盾信息：

- "用户喜欢简短回答"（半年前）
- "用户希望详细解释"（昨天）

**解法**：

- **写入时去重**：先检索是否已有相似记忆，更新 vs 新增
- **冲突解决**：旧记忆和新记忆冲突 → 标"已修正"或删除
- **TTL / 重要度**：低重要度记忆给 TTL；定期清理
- **遗忘策略**：模拟人的遗忘曲线，访问频率低的记忆衰减

---

## 六、记忆的检索策略

### 1. 简单语义检索

```python
relevant = vector_db.query(embedding(user_query), top_k=5)
prompt += "\n\n相关历史：\n" + "\n".join(relevant)
```

够用但有问题：用户问"我喜欢什么"，检索可能召回十段语义相关但都不对的话。

### 2. Hybrid Retrieval（语义 + 关键词）

```python
results = combine(
    vector_search(query),
    keyword_search(query)
)
```

详见 [../rag/retrieval-basics.md](../rag/retrieval-basics.md)。

### 3. 时间加权

```python
score = similarity * exp(-decay * age_days)
```

最近的记忆权重更高，远期记忆衰减——"刚说的"比"半年前说的"更可能相关。

### 4. 多路召回 + Rerank

```
路 1: 语义检索 5 条
路 2: 关键词检索 5 条
路 3: 同类型记忆 5 条
合并 → Cross-encoder rerank → top-3 注入
```

生产 Agent 标准做法。

### 5. 主动检索（Agentic Retrieval）

让 Agent 自己决定要不要检索 / 检索什么：

```
Thought: 这个问题涉及用户偏好，我需要查 memory
Action: search_memory(query="用户在 PRD 风格上的偏好")
Observation: ...
```

适合复杂场景，但开销大。

---

## 七、写好记忆的"三层抽象"（参考 Letta / MemGPT 思想）

```
┌─────────────────────────────────────────┐
│ Working Memory（工作记忆）               │
│   当前任务上下文 → in-context             │
└─────────────────────────────────────────┘
              ↑↓
┌─────────────────────────────────────────┐
│ Recall Memory（召回记忆）                │
│   历史会话片段 → 向量检索                 │
└─────────────────────────────────────────┘
              ↑↓
┌─────────────────────────────────────────┐
│ Archival Memory（归档记忆）              │
│   长期事实 / 文档 → 向量库                │
└─────────────────────────────────────────┘

LLM 通过工具调用在三层间"翻页"：
  - read_recall(query)
  - write_archival(fact)
  - search_archival(query)
```

这种设计让 LLM**自己负责**记忆管理——和操作系统的内存层级类比。

---

## 八、典型 Agent 记忆架构示例

### Coding Agent（如 Cursor / Claude Code）

```
短期: 当前文件 + 最近 N 个文件 + 最近 K 步骤
长期:
  - 项目知识：CLAUDE.md / README / 代码符号索引
  - 用户偏好：~/.claude/MEMORY.md（本工作区就是这个模式）
  - 经验教训：每个项目的 ANTI-PATTERNS.md
```

### 客服 Agent

```
短期: 当前会话
长期:
  - 用户档案（订单历史、投诉记录） → KV 数据库
  - 知识库（FAQ、产品手册） → 向量库
  - 对话历史 → 向量库 + 时间索引
```

### 研究 Agent（Deep Research）

```
短期: 当前任务的探索链
中期: 本次研究中累计的笔记和引用
长期: 跨研究的"主题专家知识"（很少实现）
```

---

## 九、几个反直觉的观察

### 1. "上下文窗口越大，越不需要记忆"——错
- 即使 200K context，无差别塞进去会让模型 "lost in the middle"
- 需要的是**正确的信息在正确的位置**，不是"所有信息都在"

### 2. "记忆越多 Agent 越聪明"——错
- 记忆质量比数量重要
- 噪音多的 memory 让 Agent 更易胡说

### 3. "纯向量库够用了"——通常错
- 向量库召回精度有限，结构化数据 + 关系数据效果更好
- 头部产品都是 Hybrid

### 4. "实现 memory 是技术问题"——更多是产品问题
- 写什么、什么时候写、什么时候用——这些都是产品决策
- 工程难，但产品定义更难

---

## 十、Checklist

```
□ 1. 我区分了短期和长期记忆吗？
□ 2. 长期记忆按内容类型（profile / episodic / semantic / procedural）分类了？
□ 3. 写入是有触发条件的，还是无差别写？
□ 4. 有去重 / 更新 / 冲突解决机制吗？
□ 5. 检索是单路向量检索，还是混合 + rerank？
□ 6. 用户能查看 / 修改 / 删除自己的 memory 吗？
□ 7. 有"敏感信息"过滤（避免 PII 泄漏）？
□ 8. 评测里有"记忆相关任务"专项？
```

---

## 十一、扩展阅读

- 本目录：[react-and-variants.md](react-and-variants.md)
- **方案对比**：[openviking-vs-hindsight.md](openviking-vs-hindsight.md) — 两种主流"长期记忆 Provider"的原理 / 实现 / 在 ice-workbench 中怎么用
- 相关：[../rag/retrieval-basics.md](../rag/retrieval-basics.md)、[../tools-protocols/mcp.md](../tools-protocols/mcp.md)
- Packer et al. (2023) — *MemGPT: Towards LLMs as Operating Systems*
- Letta（MemGPT 团队后续）：https://www.letta.com
- Mem0：https://github.com/mem0ai/mem0
- Lilian Weng — *LLM Powered Autonomous Agents*（其中"Memory"章节）
- Andrej Karpathy — *Software 3.0* 中关于"AI 操作系统"的讨论
- 本工作区根目录的 [AGENTS.md](../../../AGENTS.md)、[MEMORY.md](../../../MEMORY.md) 即记忆系统的极简实现
