# Agent 协作 Hook 机制

> Hook是在任务生命周期关键点自动触发的自动化脚本，实现任务识别、规则校验、流程自动化，减少人工干预。

## Hook 触发点（任务生命周期）

```
用户输入 → [ pre_task 前置Hook ]
    ↓
    任务类型识别、规则校验、优先级判断、冲突检测
    ↓
Coordinator拆解派单 → [ pre_dispatch 派单前Hook ]
    ↓
    检查子Agent执行条件、准备上下文
    ↓
子Agent执行 → [ post_execution 执行后Hook ]
    ↓
    结果校验、格式检查、错误检测
    ↓
交付用户 → [ post_task 任务后Hook ]
    ↓
    自动归档、知识沉淀、记忆更新、索引维护
```

## Hook 列表

| Hook名称 | 触发点 | 功能 | 脚本 | 状态 |
|----------|--------|------|------|------|
| 任务分类器 | pre_task | 自动识别任务类型，判断是否需要派单给DataAnalyst/DocWriter | `task_classifier.py` | ✅ 已实现 |
| 规则校验器 | pre_task | 自动检查任务是否违反AGENTS.md业务踩坑硬规则，违规直接拦截 | `rule_checker.py` | ✅ 已实现 |
| 优先级检查器 | pre_task | 判断任务优先级，P2/明确不做清单内的任务直接拒绝 | `priority_checker.py` | ✅ 已实现 |
| 结果校验器 | post_execution | 校验结果数据标注/结论先行/结构化，无来源数据按护栏G4拦截 | `result_validator.py` | ✅ 已实现 |
| 知识沉淀提示 | post_task | 判断是否有可复用资产，提示沉淀到知识库/数据资产层 | `knowledge_recall.py` | ✅ 已实现 |
| 自动归档器 | post_task | 任务完成后归档文档、更新索引、三处备份 | `auto_archiver.py` | 🔜 规划中 |

> **触发方式（现状）**：Hook 目前是**手动 CLI**，非自动挂载——`python run_hooks.py <触发点> "<内容>"`，由 Coordinator 在任务关键点按需调用。
> **`auto_archiver` 为何规划中**：它涉及文件移动/覆盖，风险较高，当前归档由 DocWriter 按 `AGENTS.md` 规则手动执行（见 `.agents/doc-writer/AGENT.md`）；待流程稳定再自动化，避免误操作。

## 配置文件
Hook配置文件：`.agents/hooks/hooks_config.json`，可配置哪些Hook启用、阈值参数、跳过规则等。

## 扩展方式
新增Hook只需：
1. 在本目录添加Python脚本，实现对应逻辑
2. 在hooks_config.json中注册Hook和触发点
3. Coordinator执行任务时自动加载运行
