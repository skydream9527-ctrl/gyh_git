# AI 基础设施 — 训练、推理与工程化落地

> 大模型训练、推理、MLOps、MoE 相关知识，支撑 AI 产品从 Demo 到生产环境的稳定落地。
> 开篇导读见 [OVERVIEW.md](OVERVIEW.md)。

## 核心文件

| 文件 | 内容 |
|------|------|
| [01-distributed-training.md](01-distributed-training.md) | 分布式训练：数据并行、模型并行、张量并行、流水线并行 |
| [02-training-optimization.md](02-training-optimization.md) | 训练优化：混合精度、梯度累积、ZeRO、Flash Attention |
| [03-inference-serving.md](03-inference-serving.md) | 推理服务架构：vLLM、TensorRT-LLM、推理框架选型 |
| [04-inference-optimization.md](04-inference-optimization.md) | 推理优化：量化、KV Cache、投机解码、批处理 |
| [05-mlops-platform.md](05-mlops-platform.md) | MLOps 平台：模型网关、监控告警、灰度发布、版本管理 |
| [06-moe-mixture-of-experts.md](06-moe-mixture-of-experts.md) | MoE 混合专家架构：原理、发展历史、业界方案、趋势 |

## 核心关注点

- **成本 / 延迟 / 效果权衡三角**：所有基础设施决策都围绕这三者做取舍
- **模型网关路由（Mify Gateway）**：多模型统一接入、智能路由、缓存、限流
- **推理延迟优化**：从算法层到工程层的全链路优化手段
- **可观测性体系**：系统监控、成本监控、质量监控、用户反馈闭环
- **模型安全与合规**：内容安全、数据隐私、合规审计

## RAG 落地

- Linux RAG 知识库搭建完整指南（Docker + PostgreSQL/pgvector + FastAPI）在 [data-product-workspace/00-知识库/ai-infra/](../data-product-workspace/00-知识库/ai-infra/methods/rag/Linux_RAG知识库搭建指南.md)

## 与本工作区的关联

- 上层 Agent 和 LLM 应用 → [../agent-llm/](../agent-llm/)
- 技术选型决策 → [../decision-frameworks/](../decision-frameworks/)
