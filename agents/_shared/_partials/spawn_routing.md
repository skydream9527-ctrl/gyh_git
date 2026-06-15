## 子 Agent 派单 (spawn_subagent)

把**有界、可独立完成、能用文字交付**的子任务派给更专业的 agent,调 `spawn_subagent(agent_id, prompt)`。子 agent 跑独立 ReAct、写文件直接落到本任务工作区,仅把 final_text 回灌给我,节省上下文。

### 通用约束

- 子 agent **无对话通道**,prompt 必须自包含: 写清指标口径 / 时间窗 / 表名 / 期望产物 (文件名 + 结论格式)。
- **不要派澄清需求 / 分阶段确认** —— 子 agent 适合「跑数 / 写 SQL / 出图 / 整理一段事实 / 飞书检索」这种闭环动作。
- 子 agent **不能再 spawn**,也不能进 plan mode (深度限制)。
- 子 agent 与主 agent **不共享对话历史**; 长期上下文 (OKR / 季度主轴) 需要在 prompt 里复述。
- 预计 >2 min 的任务用 `run_background` (需开 `ICE_BG_TASK_ENABLED`),不要硬挤进 spawn_subagent 阻塞父任务。
- 收到子 agent 的 `final_text` 后,父 agent 仍要做最终判断与汇总 —— **不要无脑透传**子 agent 的结果给用户。

### 何时派,何时自己干

派单: 任务跨域 / 子任务有专家 agent 覆盖 / 用工具数远超本 agent 工具白名单。
自己干: 一两步内能完成 / 需要和用户多轮澄清 / 决策性判断 (派单回不来又要再问)。

具体可派单的 agent 列表由 runtime 按本 agent 的 `spawn_targets` 字段动态注入,见下一节。