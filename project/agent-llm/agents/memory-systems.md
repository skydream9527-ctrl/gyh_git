# Agent 记忆系统

> 让 Agent "**记住**" 是从原型到产品最大的鸿沟之一。本文系统讲清记忆的分类（短期/长期、Episodic/Semantic/Procedural）、工程实现（窗口/摘要/向量/图）、以及生产环境的取舍。

---

## 零、三问三答：什么是记忆？主流方案？实现原理？

### Q1：什么是 Agent 的记忆？

**一句话**：记忆是让 LLM 这个**无状态**的"单次推理引擎"跨步骤、跨会话保留信息的外部机制。

LLM 本身每次调用都是从零开始——它没有内置的"记住上一句"能力。你觉得 ChatGPT 能"记住"你刚才说的话，是因为**客户端把历史对话每次都重新塞回 prompt 里**。当历史太长塞不下了、或者你下次新开一个对话，它就"忘了"。

所以 Agent 的记忆本质上解决两件事：

1. **单次会话内不被上下文窗口卡住**（短期记忆）
2. **跨会话保留用户偏好、事实、经验**（长期记忆）

没有记忆的 Agent 就像一个失忆症患者——每一步都像第一次见面，无法完成任何多步任务，也无法建立用户黏性。

### Q2：当前主流解决方案是什么？

业界没有银弹，但已经收敛到一套**分层混合（Hybrid）架构**，几乎所有头部产品（ChatGPT Memory、Claude Projects、Cursor、Claude Code）都在这个框架内：

```
┌─────────────────────────────────────────────────────┐
│  Layer 1: 短期记忆（Working Memory）                 │
│  滑窗 + 摘要 → 放上下文窗口                         │
├─────────────────────────────────────────────────────┤
│  Layer 2: 长期记忆（Long-term Memory）— 混合存储    │
│  ├─ KV/结构化  → 用户画像、偏好、固定属性            │
│  ├─ 向量库     → 历史对话、语义事实（语义检索）      │
│  └─ 图数据库   → 实体关系（复杂场景才用）            │
├─────────────────────────────────────────────────────┤
│  Layer 3: 记忆管理层                                │
│  写入策略（何时写）+ 检索策略（何时读、怎么召回）    │
│  + 去重/更新/遗忘机制                               │
└─────────────────────────────────────────────────────┘
```

**主流方案的三个共识**：

| 共识 | 说明 |
|---|---|
| **不要纯靠上下文窗口** | 即使 200K context，无差别塞入会导致 lost-in-the-middle 和成本爆炸 |
| **向量库不是万能的** | 纯向量检索召回精度有限，结构化 KV 存偏好/Profile 效果更可控 |
| **写入比检索难** | "写什么"比"怎么存"重要 10 倍——噪音记忆比没记忆更糟 |

开源/商业方案速览：

- **Mem0**（开源）：通用记忆层，自动提取事实、去重、更新，API 简单，适合快速接入
- **Letta / MemGPT**（开源）：操作系统式三层记忆（Working/Recall/Archival），LLM 自己管理翻页
- **LangChain Memory**：提供 ConversationSummaryBufferMemory、VectorStoreRetrieverMemory 等组件
- **ChatGPT Memory / Claude Projects**：商业产品的 Hybrid 实现，自动提取偏好+语义检索
- **Zep / Motorhead**：专为 Agent 设计的记忆服务，带时间加权检索和摘要

### Q3：记忆实现的原理是什么？

记忆系统的核心原理可以拆成**写入路径**和**读取路径**两条流水线，外加**上下文管理**机制：

#### 原理 1：短期记忆——上下文窗口管理

LLM 的"记忆"就是 prompt 里的 messages 数组。短期记忆管理本质是**决定往 prompt 里放什么**：

```
朴素做法（Sliding Window）：
  messages = messages[-N:]  → 只保留最近 N 条，简单但丢信息

主流做法（Summary + Window）：
  if 消息超过阈值 K:
      早期消息 → LLM 摘要 → 压缩成一段系统提示词
      保留最近 K 条原始消息
      → [摘要] + [最近 K 条] 一起放进 prompt

进阶做法（Hierarchical Summary）：
  原始消息 → 微摘要 → 大摘要 → 长期事实
  类似内存层次结构：寄存器 → L1/L2 Cache → 内存 → 磁盘
```

**关键原理**：LLM 的上下文窗口有限且贵，必须通过**摘要压缩**延长会话长度，同时保留关键信息。

#### 原理 2：长期记忆——Embedding + 向量检索

长期记忆的核心是**语义检索**：

```
写入流程：
  对话内容 / 关键事实
    → 用 LLM 提取值得记忆的片段（"用户喜欢先结论后细节"）
    → 用 Embedding 模型转成向量（如 text-embedding-3-small → 1536 维向量）
    → 存入向量数据库（Pinecone / Qdrant / PG Vector / Milvus）

读取流程：
  当前用户提问 → Embedding 转成向量
    → 在向量库里做相似度搜索（余弦距离/内积）
    → 召回 Top-K 最相关的历史记忆
    → 作为 "[相关历史]" 注入 prompt 的 system message 中
    → LLM 看到这些信息，就能"想起来"
```

**关键原理**：Embedding 把文本映射到高维语义空间，意思相近的文本向量距离近，从而实现"语义搜索"而不是关键词匹配。

#### 原理 3：结构化记忆——KV/Profile

对于稳定属性（用户名、角色、偏好），用向量检索是杀鸡用牛刀：

```
写入：对话中检测到 "我是产品经理" → {"role": "产品经理"} 写入 KV 存储
读取：每次对话开头直接读取 profile，拼进 system prompt
```

这类记忆 100% 可控，不存在召回错误。

#### 原理 4：记忆管理——写入触发 + 冲突解决

```
写入触发（不是什么都记）：
  ✅ 用户明确说"记住这个"
  ✅ 表达偏好（"我喜欢..."）
  ✅ 关键决策、校正信息
  ❌ 闲聊、一次性查询

冲突解决：
  新记忆 "我希望详细解释" vs 旧记忆 "用户喜欢简短回答"
    → 检索相似记忆 → 判断是否矛盾 → 更新/替换/标记过期

遗忘机制：
  时间衰减：score = similarity × exp(-decay × days)  越久远权重越低
  重要度打分：关键决策永不过期，临时信息 TTL 自动过期
```

**核心原理总结**：Agent 记忆 = **上下文窗口管理**（短期）+ **语义检索**（长期向量）+ **结构化存储**（长期 KV）+ **写入/更新策略**（管理层）。它不是 LLM 本身"会记"，而是**工程层在 prompt 外维护了一个信息检索系统**，在需要时把正确的信息塞回 prompt。

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
