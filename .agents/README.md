# 多Agent协作体系

> 本目录定义数据产品工作Agent的角色分工、协作流程和职责边界。

## 核心角色

| 角色 | 定义文件 | 核心职责 |
|------|----------|----------|
| Coordinator（协调者） | [coordinator/AGENT.md](./coordinator/AGENT.md) | 任务入口、需求理解、拆解分配、结果汇总、质量校验、决策辅助 |
| DataAnalyst（数据分析师） | [data-analyst/AGENT.md](./data-analyst/AGENT.md) | SQL生成、数据查询、口径校验、结果分析、数据报告产出 |
| DocWriter（文档工程师） | [doc-writer/AGENT.md](./doc-writer/AGENT.md) | 内容结构化、格式优化、飞书同步、文档归档、索引更新 |

## 协作流程

```
用户需求 → Coordinator入口
    ↓
    ├─ 需求理解与拆解，生成任务单
    ├─ 判断是否需要数据支持 → 是 → 派单给DataAnalyst
    ├─ 判断是否需要文档输出 → 是 → 派单给DocWriter
    ↓
    各角色执行任务 → 返回结果给Coordinator
    ↓
    Coordinator汇总校验 → 交付用户 → 触发知识沉淀流程
```

## 任务工作目录

所有任务在 `08-任务协作/` 目录下按任务ID管理：
- `进行中/`：正在执行的任务
- `待归档/`：已完成等待归档沉淀的任务
- `已完成/`：已完成归档的任务历史

## 调用规则

1. 所有用户请求首先进入Coordinator，禁止直接调用子Agent
2. 子Agent只处理Coordinator分配的明确任务，不直接响应用户
3. 跨角色依赖由Coordinator协调，子Agent之间不直接通信
4. 任务产出必须经过Coordinator质量校验后才能交付用户
