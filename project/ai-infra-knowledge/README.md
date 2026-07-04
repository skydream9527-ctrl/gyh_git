# AI基础设施 — 训练、推理与工程化落地

> 大模型训练、推理、MLOps、RAG相关知识，支撑AI产品从Demo到生产环境的稳定落地。

## 目录导航

| 目录 | 内容 |
|------|------|
| [concepts/](./concepts/) | 核心概念：分布式训练、训练优化技术原理 |
| [methods/](./methods/) | 落地方法：推理服务、推理优化、MLOps平台、RAG知识库搭建 |
| [pitfalls/](./pitfalls/) | 踩坑记录：工程落地常见问题与解决方案 |
| OVERVIEW.md | 开篇导读，建立AI基础设施心智模型 |

### 核心文件
| 文件 | 内容 |
|------|------|
| [concepts/01-distributed-training.md](./concepts/01-distributed-training.md) | 分布式训练原理：数据并行、模型并行、张量并行、流水线并行 |
| [concepts/02-training-optimization.md](./concepts/02-training-optimization.md) | 训练优化技术：混合精度训练、梯度累积、ZeRO优化、Flash Attention |
| [methods/03-inference-serving.md](./methods/03-inference-serving.md) | 推理服务架构：vLLM、TensorRT-LLM、推理框架选型 |
| [methods/04-inference-optimization.md](./methods/04-inference-optimization.md) | 推理优化：量化、KV Cache、投机解码、批处理、延迟/成本优化 |
| [methods/05-mlops-platform.md](./methods/05-mlops-platform.md) | MLOps平台：模型网关、监控告警、灰度发布、版本管理、成本优化 |
| [methods/rag/Linux_RAG知识库搭建指南.md](./methods/rag/Linux_RAG知识库搭建指南.md) | Docker+PostgreSQL/pgvector+FastAPI完整RAG部署方案，含docker-compose配置、API设计、生产建议 |

## 核心关注点
- **成本/延迟/效果权衡三角**：所有基础设施决策都围绕这三者做取舍
- **模型网关路由（Mify Gateway）**：多模型统一接入、智能路由、缓存、限流
- **推理延迟优化**：从算法层到工程层的全链路优化手段
- **可观测性体系**：系统监控、成本监控、质量监控、用户反馈闭环
- **模型安全与合规**：内容安全、数据隐私、合规审计

## 与本工作区的关联
- 上层Agent和LLM应用 → [../agent-llm/](../agent-llm/)
- AI产品设计方法 → [../product/](../product/)
- 技术选型决策 → [../decision-frameworks/](../decision-frameworks/)
