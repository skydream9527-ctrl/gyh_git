# RAG Web UI 入门教程：知识库 QA 系统全流程

> 来源: https://github.com/rag-web-ui/rag-web-ui/blob/main/docs/tutorial/README.md

---

## 1. 什么是 RAG

RAG (Retrieval-Augmented Generation，检索增强生成) 将检索系统与生成式 AI 结合：

1. **检索**：根据用户问题从知识库检索相关文档片段
2. **生成**：将检索结果作为上下文，让 LLM 生成准确回答

### 三种方案对比

| 方案 | 优点 | 缺点 |
|------|------|------|
| 传统检索式 QA | 可靠、可更新 | 灵活性差、表达生硬 |
| 纯 LLM | 表达自然、理解灵活 | 知识固化、易幻觉 |
| **RAG** | 可靠+可溯源+可更新+表达自然 | 架构复杂度略高 |

### 典型应用场景

- 企业内部员工知识库 / 对外客户问答
- 法律法规、学术论文等需要引用来源的场景
- 任何需要"带引用信息"的回答场景

---

## 2. 系统架构与核心组件

### 核心组件

| 组件 | 作用 |
|------|------|
| 向量数据库 | 存储文档分块向量（ChromaDB、Qdrant 等）|
| Embedding 服务 | 将文本转为数值向量 |
| 检索模块 | 按向量相似度检索最相关片段 |
| LLM | 结合上下文生成带引用的最终回答 |

### 技术栈（rag-web-ui 项目）

- **前端**：React (Next.js) + TailwindCSS + AI SDK
- **后端**：FastAPI + LangChain + ChromaDB/Qdrant + MySQL + MinIO
- **部署**：Docker + Docker Compose

### 典型查询工作流

```
用户问题 → Embedding → 向量检索 → Rerank 重排 → 上下文组装 → LLM 生成 → 带引用的回答
```

---

## 3. 文档处理：分块、向量化、存储

### 3.1 为什么要分块（Chunking）

1. 向量相似度精度：短文本向量更精确，捕捉局部语义更好
2. LLM 上下文窗口有限制
3. 检索效率与成本：只取最相关片段，减少无关信息
4. 引用溯源：精确定位到具体段落

### 3.2 常见分块策略

| 策略 | 特点 | 适用场景 |
|------|------|---------|
| 固定长度 | 实现简单，可能切断语义 | 结构统一文档 |
| 语义分块 | 按段落/章节切分，保持连贯 | 结构化文档 |
| 重叠分块 | 相邻块保留重叠，避免关键信息丢失 | 通用场景 |
| 递归分块 | 先大块后细分，保持层次 | 长文档 |

**实践建议**：Markdown 按段落分块；通用文档按章节分块。

### 3.3 Embedding 模型选择

| 模型 | 特点 |
|------|------|
| `text-embedding-ada-002` | 多语言，中文支持较弱，1536 维 |
| `bge-large-zh` | 中文效果好 |
| `multilingual-e5-large` | 多语言均衡支持 |
| `CodeBERT` | 专门用于代码文本 |

### 3.4 向量存储数据结构

```json
{
  "id": "chunk_id",
  "text": "段落内容",
  "metadata": {
    "source": "文档来源",
    "position": "段落位置",
    "hash": "段落哈希值"
  }
}
```

**支持的向量数据库**：ChromaDB、Qdrant、Milvus、Faiss、Annoy、Pinecone、Zilliz（通过 Factory 模式切换）

---

## 4. 检索与重排序

### 4.1 相似度计算方法

| 方法 | 公式 | 特点 |
|------|------|------|
| 余弦相似度（默认） | cos(θ) = A·B / (‖A‖·‖B‖) | 不受向量长度影响，最常用 |
| L2 欧氏距离 | d = √Σ(ai-bi)² | 对向量长度敏感 |
| 内积 IP | Σ(ai×bi) | 计算快速 |

### 4.2 重排序（Re-ranking）

两阶段流程：
1. **初步检索**：向量相似度快速召回候选文档（20-100 条）
2. **Cross-Encoder 重排**：对候选文档精细打分，理解 query 与文档的语义关联

适用场景：多路召回结果统一排序、高精度要求、复杂查询。

---

## 5. 上下文组装与引用格式

### 系统 Prompt 模板（关键）

```python
qa_system_prompt = (
    "You are given a user question, and please write clean, concise and accurate answer to the question. "
    "You will be given a set of related contexts to the question, which are numbered sequentially starting from 1. "
    "Please use these contexts and cite them using the format [citation:x] at the end of each sentence where applicable. "
    "If a sentence draws from multiple contexts, please list all applicable citations, like [citation:1][citation:2]. "
    "Other than code and specific names and citations, your answer must be written in the same language as the question. "
    "Context: {context}"
)
```

### 前后端数据协议

- 响应格式：`{context_base64}__LLM_RESPONSE__{answer}`
- `context`：Base64 编码的检索切片数组
- `answer`：LLM 生成的回答，包含 `[[citation:1]]` 引用标记
- 前端解析引用标记后渲染弹窗，展示知识库名、文件名、引用原文

---

## 6. 文档上传异步处理流程

```
上传文档 → 存 NFS → 创建 Job → 返回 Job ID
→ 异步Worker: 文本提取 → 分块 → Embedding → 存向量库 → 更新状态
← 客户端轮询 Job ID 查进度
```

**关键设计**：更新文档时使用临时表，确保新文件处理完成后才删除旧向量，避免检索结果断档。

---

## 7. 进阶方向

- **多路召回**：多个数据库或不同关注点的检索结果合并
- **RAG + Cross-Encoder Rerank**：提高回答精度
- **长文本多轮对话**：Conversation Memory / 上下文记忆
- **HyDE**（Hypothetical Document Embeddings）：用假设文档辅助检索
- **Query 改写**：对用户查询预处理提升召回质量

---

## 8. 关键代码位置（rag-web-ui 项目）

| 功能 | 文件路径 |
|------|---------|
| 文档处理 | `backend/app/services/document_processor.py` |
| 向量库 Factory | `backend/app/services/vector_store/factory.py` |
| RAG 检索 + LLM 生成 | `backend/app/services/chat_service.py` |
| 引用渲染组件 | `frontend/src/components/chat/answer.tsx` |
| Chat 页面 | `frontend/src/app/dashboard/chat/[id]/page.tsx` |
