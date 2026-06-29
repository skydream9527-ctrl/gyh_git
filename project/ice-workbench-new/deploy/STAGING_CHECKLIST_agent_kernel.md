# Staging 验证清单 — 统一 agent_kernel 迁移

适用对象：把用户对话路径从 ws.py 内置循环切到统一内核 `agent_kernel` 的灰度上线。

**为什么需要这份清单**：子 agent / 后台 / 调度器路径已经走内核，并被 399 个单测锁定行为。但**用户对话（WebSocket 流式）这条路没有自动化集成测试**——切换只保证了「编译 + 导入 + 逐帧设计对齐」，运行时行为必须人工在 staging 验证。

---

## 0. 背景：这次改了什么

把两套重复的 ReAct 循环收敛成一份内核：

| 文件 | 角色 |
|------|------|
| `backend/app/services/agent_kernel.py` | 统一 ReAct 内核 + `EventSink` 接口 + `AgentState` |
| `backend/app/services/agent_event_sinks.py` | `TranscriptEventSink`（子 agent / 后台 / 调度器审计） |
| `backend/app/services/agent_runtime.py` | 薄适配层，委托给内核（已被单测锁定） |
| `backend/app/api/v1/ws_event_sink.py` | `WebSocketEventSink`，逐帧复刻流式协议 |
| `backend/app/api/v1/ws.py` | 灰度分支：`if s.ICE_AGENT_KERNEL_ENABLED:` 走内核，否则老循环 |

切换开关：**`ICE_AGENT_KERNEL_ENABLED`**（默认 `false`，老循环为默认路径）。

---

## 1. 上线前置（代码层，已完成）

- [x] 全量单测通过：`cd backend && . .venv/bin/activate && pytest -q` → **399 passed, 1 skipped**
- [x] 所有改动文件字节编译通过
- [x] 应用在开关 on / off 两种状态下都能正常 import / boot
- [x] 内核功能冒烟（纯文本 / 工具轮 / 并行工具 / plan 中止 / 中途 abort / LLM 错误两种路径）全过

> 这些在开发环境已验证。下面是 **staging 上必须人工过的运行时链路**。

---

## 2. Staging 开启开关

```bash
# 在 staging 的 .env 里设置
ICE_AGENT_KERNEL_ENABLED=true

# 重启服务使其生效
./deploy.sh --prod    # 或 make prod / 重启容器

# 确认开关已读到
curl -fs http://<staging>:8000/api/v1/health
```

> 建议保留一台未开开关的对照实例，必要时 A/B 对比同一 prompt 的输出。

---

## 3. 功能链路验证（逐项勾选）

### 3.1 基础流式对话
- [ ] 发一条普通问题，**文字逐字流式**出现（不是一次性整段蹦出来）
- [ ] 回答完成后出现 `agent_message_done`，输入框恢复可用
- [ ] 刷新页面后，该轮对话**完整保存**在历史里（assistant 消息 + 文本一致）

### 3.2 单工具调用
- [ ] 触发一次工具（如 `now` / `kyuubi_query`）：前端依次出现 `tool_call_start` → `tool_call_done`
- [ ] 工具结果回灌后模型给出最终回答
- [ ] 「运行事件」时间轴里 `模型生成中` → `开始执行 X` → `X 执行结束` → `执行完成` 顺序正确

### 3.3 多工具 / 并行（需同时开 `ICE_PARALLEL_TOOLS_ENABLED`）
- [ ] 一轮内多个只读工具**并行**执行（UI 同时转圈），非只读工具串行
- [ ] 关掉 `ICE_PARALLEL_TOOLS_ENABLED` 后退回串行，行为正常

### 3.4 文件产物
- [ ] 触发 `write_file` / `execute_python` 产出文件：左侧文件面板**即时出现** `file_created`
- [ ] 文件可打开 / 下载，内容正确

### 3.5 中断（abort）
- [ ] 生成中途点「中断」：流式停止，已生成的部分文本**被保存**进历史（`stop_reason=user_aborted`）
- [ ] 中断后可继续追问，对话不卡死（无 `CONVERSATION_INFLIGHT` 误报）

### 3.6 Plan 审批流（需开 `ICE_PLAN_MODE_ENABLED`）
- [ ] 触发 `exit_plan_mode`：收到 `plan_proposed`，UI 进入「等待用户审批方案」
- [ ] 批准后 agent 继续执行；拒绝后正确终止

### 3.7 人工介入（如启用 `request_human_input`）
- [ ] 触发后收到 `human_intervention`，UI 进入「等待人工确认」

### 3.8 子 agent / 后台 / 定时任务（回归，确认未被影响）
- [ ] `spawn_subagent` 派单子 agent 正常返回（需 `ICE_SUBAGENT_ENABLED`）
- [ ] `run_background` 后台任务跑完发通知（需 `ICE_BG_TASK_ENABLED`）
- [ ] 已有定时任务到点正常触发

### 3.9 异常路径
- [ ] LLM 网关报错时：前端收到 `error` 帧（`GATEWAY_ERROR` 或原始 error_code），运行事件标「执行失败」，**不是无限转圈**
- [ ] 工具失败：`tool_call_done` 带 `success=false` + error，模型能继续处理

---

## 4. 一致性 / 性能 / 稳定性

- [ ] 用同一组 prompt 对比「开关 on」与「开关 off」的输出，**无明显质量回退**
- [ ] 多用户/多会话并发下无串话、无 ws 误关、无 keepalive 失效
- [ ] 长会话（触发 compaction）下正常，无 400 orphan tool_use 报错
- [ ] 观察 token 用量（`usage_svc`）记录正常，未异常翻倍

> ⚠️ **已知的一处刻意差异**：内核回灌给模型的 `tool_result` 序列化采用 Anthropic 规范形式（字符串结果直接透传、`is_error` 仅失败时出现）。对**返回 dict 的工具**（绝大多数）与老 ws 路径完全一致；仅当工具返回**纯字符串**时，老路径会多一层 JSON 引号。重点观察返回字符串结果的工具是否表现正常。

---

## 5. 上线决策

- [ ] 上述链路**全部通过** → 可在生产开 `ICE_AGENT_KERNEL_ENABLED=true`
- [ ] 任一项异常 → 关开关回退老循环（**零风险，老代码原样保留**），记录问题后修复再试

回退方式（即时生效，无需回滚代码）：
```bash
# .env
ICE_AGENT_KERNEL_ENABLED=false
# 重启服务
```

---

## 6. 稳定后的收尾（后续单独 PR）

内核路径在生产稳定运行一段时间（建议 ≥ 1～2 周）后：

- [ ] 删除 `ws.py` 里 `if s.ICE_AGENT_KERNEL_ENABLED:` 之外的**老循环 else 分支**，彻底消除重复
- [ ] 视情况移除 `ICE_AGENT_KERNEL_ENABLED` 开关（让内核成为唯一路径）
- [ ] 补一个 ws 流式路径的最小集成测试，填上当前的自动化覆盖缺口
