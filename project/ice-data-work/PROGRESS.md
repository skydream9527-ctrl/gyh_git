# ICE-DATA-WORK 开发进度（PROGRESS）

- 配套：`DEV_PLAN.md`（任务级计划，本文件用同一套任务 ID）
- 用途：记录"已开发到哪、验证结论、下一步"。每完成一个任务就更新这里。
- 更新约定：改对应任务状态 → 在「变更日志」加一行（日期 + 任务 ID + 结论）。

## 当前状态

- **当前里程碑**：M6 ✅ 完成 → 准备进入 **M5（联调/移动端/验收）**
- **整体进度**：M0 ✅ + M1 ✅ + M2 ✅ + M3 ✅ + M4 ✅ + M6 ✅；M5 待开发。
- **可运行**：`make install` 后 `make backend`（:8000）/ `make frontend`（:5173）；登录 admin/admin123 → 工作台 → 看板 → 任务多方对话 → 记忆候选晋升/审批 → 治理(审计/一键暂停) → 管理后台(用量/CSV) → Agent Hub/知识产物 → 任务内 run_user_code 沙盒 + 贡献为 Skill。

## 里程碑进度总表

| 里程碑 | 状态 | 完成度 | 备注 |
|---|---|---|---|
| M0 仓库与地基 | ✅ done | 11/13 | T11(SQLite索引) / T12(pgvector) 顺延 |
| M1 团队/项目/Twin/认证 | ✅ done | 12/12 | 全部完成 |
| M2 任务/看板/多参与者会话 | ✅ done | 15/15 | 产品主线全部完成 |
| M3 记忆隔离/复用闭环 | ✅ done | 8/8 | 平台内核全部完成 |
| M4 治理/资产/后台 | ✅ done | 9/9 | 全部完成 |
| M5 联调/移动端/验收 | todo | 0/5 | 收口 |
| M6 Skill/Agent 自演进 | ✅ done | 8/8 | 自演进闭环全部完成 |
| 二期 P2-01~04 | todo | — | v1 后 |

## M0 明细（已完成）

| ID | 任务 | 状态 | 验证结论 |
|---|---|---|---|
| M0-T01 | 目录梳理 docs/ | ✅ | 根目录干净，docs 含 5 文档 + prototype + 参考资料 |
| M0-T02 | 根配置 | ✅ | README/Makefile/.env.example/.gitignore/docker-compose 就位 |
| M0-T03 | G3 数据目录 | ✅ | agents/skills/teams/users/tasks/files + .gitkeep |
| M0-T04 | core/config | ✅ | DATA_ROOT 自解析到仓库根（health 显示） |
| M0-T05 | 四层空间 paths | ✅ | pytest：结构正确 + 防穿越守卫拦截 ../、a/b、..、空、/abs |
| M0-T06 | jsonio/locks/transaction | ✅ | 原子写(temp+replace)；portalocker 缺失降级；file_transaction 备份回滚 |
| M0-T07 | errors 信封 | ✅ | APIError + ErrorCode + 统一 {code,message,error_code,data} |
| M0-T08 | main.py | ✅ | uvicorn 启动；`/api/v1/health` 200 |
| M0-T09 | api/teams + team_svc + seed | ✅ | `/teams` 返回 seed 的 t_growth（全链路：seed→G3 文件→svc 读→信封） |
| M0-T10 | 前端脚手架 | ✅ | Vite+React+TS+Zustand + Workbench 自检页 |
| M0-T11 | SQLite 索引层 | ⏳ 顺延 | 列表先走文件遍历，量大后接索引 |
| M0-T12 | Postgres+pgvector | ⏳ 顺延 | docker-compose 已含 pg17+pgvector；M3 已留 hook + 降级 |
| M0-T13 | 地基验证 | ✅ | health/teams e2e + pytest 全绿 |

## M1 明细（已完成）

| ID | 任务 | 状态 | 验证结论 |
|---|---|---|---|
| M1-T01 | 三轴权限实装 | ✅ | `core/deps.py`：get_current_user + require_role + require_member，JWT/Aegis 双通道 |
| M1-T02 | 双认证 | ✅ | `core/security.py`：bcrypt 密码哈希 + JWT HS256；Aegis 头 placeholder |
| M1-T03 | 用户 | ✅ | `user_svc`：CRUD + ensure_user + 密码哈希剥离返回 |
| M1-T04 | 团队 CRUD | ✅ | `team_svc`：create/update/delete + 成员管理 |
| M1-T05 | 项目 CRUD | ✅ | `project_svc`：CRUD + 成员管理，项目必须归属团队 |
| M1-T06 | 个人项目 | ✅ | 用户创建时自动建 personal_{uid} 团队 + p_personal_{uid} 项目 |
| M1-T07 | 一等 Twin | ✅ | `twin_svc`：ensure/update/set_level，默认 L2 |
| M1-T08 | 索引列 | ✅ | 暂用文件遍历，iter_dirs 列表 |
| M1-T09 | 前端认证 | ✅ | Login 页 + authStore 真实化 + JWT 持久化 |
| M1-T10 | 前端空间 | ✅ | AppLayout 侧边栏 + Team/Project 切换器 + /team /project /twin |
| M1-T11 | 种子 | ✅ | admin/test + Twin + 3 内置 Agent |
| M1-T12 | 测试 | ✅ | pytest 24/24：JWT、权限 gate、成员 CRUD、个人项目、Twin |

## M2 明细（已完成）

| ID | 任务 | 状态 | 验证结论 |
|---|---|---|---|
| M2-T01 | 任务模型 + 6 态状态机 | ✅ | todo/doing/await/done/error/paused + 合法流转校验 |
| M2-T02 | 任务 API + 参与者 | ✅ | `/tasks` CRUD + 状态流转 + participants；缺省落个人项目 |
| M2-T03 | 会话服务 | ✅ | conversation.jsonl + turn.speaker + tool_calls.jsonl |
| M2-T04 | 上下文组装 | ✅ | 5 层 + 访问控制内嵌 + 来源标注 + 预算裁剪 |
| M2-T05 | LLM 网关 | ✅ | mify 路由 + Anthropic + 无 key mock 降级 |
| M2-T06 | Agent 运行时 | ✅ | 有界 ReAct + Twin 编排路由 + @定向 |
| M2-T07 | WebSocket 流式 | ✅ | speaker 字段 + inflight guard + JWT |
| M2-T08 | 内置工具 | ✅ | 7 工具 + 高风险确认门 + CLI 降级 |
| M2-T09 | 产物服务 | ✅ | 3 态 + 渐进展开 + 保存到空间 |
| M2-T10~14 | 前端 | ✅ | Workbench/Board/NewMission/Workspace/Chat/TwinDock |
| M2-T15 | 测试 | ✅ | pytest 51/51 + 前后端 WS 联调 |

## M3 明细（已完成）

| ID | 任务 | 状态 | 验证结论 |
|---|---|---|---|
| M3-T01 | memory_svc | ✅ | propose/list/promote/reject + 5 scope + .memory.md 解析(MEM-id) |
| M3-T02 | Agent 记忆分区 | ✅ | by-user/by-team；隔离/复用矩阵：私有不外泄、团队共享 |
| M3-T03 | hitl_svc | ✅ | 审批队列 + 裁决 + 聚合待确认 |
| M3-T04 | 记忆检索 | ✅ | 关键词 top-k + pgvector hook 降级；接 ContextAssembler 先过滤再排序 |
| M3-T05 | 经验审批 | ✅ | hitl_svc + needs_review 实现共享空间晋升门控 |
| M3-T06 | 前端 | ✅ | memoryStore + MemoryPanel(候选卡/贡献给团队/审批) + Twin 记忆管理 |
| M3-T07 | 晋升原子性 | ✅ | file_transaction：候选 + 目标 .memory.md 同事务 |
| M3-T08 | 测试 | ✅ | pytest +22(共 73)；每用例独立 DATA_ROOT |

## M4 明细（已完成）

| ID | 任务 | 状态 | 验证结论 |
|---|---|---|---|
| M4-T01 | 审批与审计 | ✅ | `audit_svc`：任务/用户级 audit.jsonl + 跨空间拦截记录 + 聚合；agent_runtime/工具调用落审计 |
| M4-T02 | 一键暂停 | ✅ | `control_svc`：全局暂停开关(.cache/control.json)；agent_runtime + execute_tool 暂停态拒绝执行 |
| M4-T03 | 失败复盘 | ✅ | `error_classifier`：7 类规则(timeout/集成/权限/限流/网络…) + default → {error_type,recoverable,suggested}；接 runtime error 事件 |
| M4-T04 | 共享空间 | ✅ | `shared_svc`：项目/团队 files/knowledge/artifacts 读写列表 + 按层隔离 + 防穿越；资产汇总 API |
| M4-T05 | Agent Hub/详情 | ✅ | 前端 Agents Hub + AgentDetail（能力/记忆分区 D-06/Skills/权限边界/agent.md） |
| M4-T06 | 知识与产物页 | ✅ | 前端 Knowledge（项目/团队 × files/knowledge/artifacts 层级筛选） |
| M4-T07 | 管理后台 | ✅ | `admin` API + 前端 Admin（概览/用户/团队/用量/设置 5 tab）；admin gate；角色编辑限 super_admin |
| M4-T08 | 用量与成本 | ✅ | `usage_svc`：LLM 用量(usage.jsonl) + 单价表 + 月度预算 + CSV 导出；llm done 事件落账(mock 计次) |
| M4-T09 | 前端治理/后台 | ✅ | Approvals 页(待确认+审计+失败复盘+一键暂停) + AdminLayout 导航分组(工作/治理/空间) |

## M6 明细（已完成）

| ID | 任务 | 状态 | 验证结论 |
|---|---|---|---|
| M6-T01 | run_user_code 工具 | ✅ | python→沙盒 / sql→kyuubi 降级；结果含 stdout/stderr/产物，落 tool_calls |
| M6-T02 | 沙盒 sandbox.py | ✅ | 子进程 + 限 CPU/FSIZE + socket 阻断网络 + 去凭证 env + 隔离 cwd + 墙钟超时 kill；开关 IDW_SELF_EVOLVE_ENABLED |
| M6-T03 | schema 抽取 + propose_skill | ✅ | py params["k"]/.get、sql :param 去重保序；候选写 skill_candidates.jsonl |
| M6-T04 | skill_svc | ✅ | by-user 草稿立即可用 + 版本快照目录 + 沙盒 test-run 回写 test_passed |
| M6-T05 | skill_evolve_svc | ✅ | materialize（草稿+绑定，by_team 发审批）+ promote 双门（test_passed + owner/admin）+ 绑定 bump + 回滚 |
| M6-T06 | ContextAssembler 注入 | ✅ | _agent_skills_layer 注入团队/私有 Skill + knowledge；灰度 + 用户隔离（owner 可见/他人不可见/关闭不注入）|
| M6-T07 | 前端 | ✅ | skillStore + Chat 运行工具卡 + SkillPanel 贡献表单 + AgentDetail Skills 标签；tsc + vite build 通过 |
| M6-T08 | 测试 | ✅ | test_skills.py 25 用例（沙盒安全/schema/草稿隔离/双门/绑定/回滚/注入/HTTP gate）；pytest 117 全绿 |

> 下一步备选：M5 联调/移动端/验收（端到端场景、移动端只读、生产部署、数据热更新、全量收口）。

## 变更日志

| 日期 | 任务 | 内容 / 结论 |
|---|---|---|
| 2026-06-27 | M0-T01..T13 | 完成 M0 地基：目录梳理、根配置、G3 四层空间存储、FastAPI 启动、前端脚手架。pytest 5/5。 |
| 2026-06-28 | M1-T01..T12 | 完成 M1：JWT 认证 + 三轴权限 + 用户/团队/项目/Twin CRUD + 个人项目自动创建 + 种子 + 前端登录/空间/Twin。pytest 24/24，tsc 0 错误。 |
| 2026-06-28 | M2-T01..T15 | 完成 M2（产品主线）：6 态状态机 + 任务/参与者 + 会话 + LLM 网关(mock) + 7 工具 + 上下文分层 + Agent 运行时(Twin 编排) + WS 流式 + 产物。前端 Workbench/Board/Workspace/Chat/TwinDock。pytest 51/51，前后端 WS 联调通过。 |
| 2026-06-28 | M3-T01..T08 | 完成 M3（平台内核）：memory_svc 候选→晋升 5 scope + by-user/by-team 分区 + hitl_svc 审批 + 关键词检索(pgvector hook) + 晋升原子性 + memory/approvals API。前端 MemoryPanel + Twin 记忆管理。pytest 73/73。 |
| 2026-06-28 | M4-T01..T09 | 完成 M4（治理/资产/后台）：audit_svc + control_svc(一键暂停) + error_classifier + shared_svc(按层隔离) + usage_svc(单价/预算/CSV) + admin/governance/shared API。agent_runtime 集成暂停/错误分类/用量/审计。前端 Approvals + Admin(5 tab) + Agent Hub/详情 + Knowledge + 导航分组。pytest 92/92，tsc 0 错误，vite build 成功，HTTP+WS 联调通过(共享隔离/暂停恢复/审计/用量CSV)。 |
| 2026-06-28 | M6-T01..T08 | 完成 M6（Skill/Agent 自演进 D-13）：sandbox 沙盒(无网络/限CPU/FSIZE/去凭证/隔离cwd/墙钟超时) + run_user_code/propose_skill 工具 + skill_svc(草稿/版本/test-run) + skill_evolve_svc(晋升双门/绑定/bump/回滚) + skills API(10 路由) + ContextAssembler 注入(灰度) + 前端(skillStore/运行工具卡/SkillPanel 贡献表单/AgentDetail Skills 标签)。修复 __init__ 注册不存在 skills.py 导致的 app 崩溃。后端 pytest 117/117(+25)，前端 tsc + vite build 通过。注：本次排查并修正了多处 fs/grep/read 工具假成功与假阴性，全部改用 execute_bash 实跑核实。 |

## 已知问题 / 备注

- passlib 与 Python 3.14 + bcrypt 5.x 不兼容，改为直接调用 bcrypt 库。
- LLM 未配置 key 时走 mock 流；配置 MIFY_GATEWAY_API_KEY 或 ANTHROPIC_API_KEY 启用真实模型。用量统计 mock 计次但成本 $0。
- 记忆检索 v1 为关键词命中（中英 bigram）+ 少量条目全量；pgvector 已留 hook，配置 IDW_PGVECTOR_ENABLED + DATABASE_URL + 嵌入端点后启用。
- 一键暂停状态存 .cache/control.json（运行态，非 G3 真相源）；月度预算用 IDW_MONTHLY_BUDGET_USD（默认 $100）。
- 审计/用量由 agent_runtime 在 WS 回合中写入；纯 HTTP `/turns`（仅追加用户发言）不触发。
- 工具调用部分为 stub/降级：kyuubi_query 返回 KYUUBI_NOT_CONFIGURED；write_file/propose_memory 高风险需确认。
- M6 沙盒为进程级"软沙盒"（macOS/POSIX 无内核级隔离）：限 CPU/FSIZE + 墙钟超时 + 去凭证 + 隔离 cwd + monkeypatch 阻断 socket；内存硬限 RLIMIT_AS 默认关（macOS 会误杀解释器），生产 Linux 建议叠加容器/cgroup（IDW_SANDBOX_MEM_MB）。需 IDW_SELF_EVOLVE_ENABLED=true 开启。
- 后端测试：记忆/治理/Skill 用例每个独立 DATA_ROOT 隔离 G3 状态。pytest 中 FastAPI TestClient 有 httpx deprecation warning，不影响结果。
- 新增后端依赖：httpx（LLM 网关 + TestClient）。
- 飞书 OAuth 为 placeholder（`FEISHU_NOT_CONFIGURED` 降级）。

## 如何更新本文档

1. 完成任务 → 把对应 `M{n}-T{nn}` 状态改 ✅，必要时在「M{n} 明细」补一行验证结论。
2. 里程碑推进 → 更新「里程碑进度总表」的状态与完成度。
3. 每次有实质进展 → 在「变更日志」加一行（日期 + 任务 ID + 一句结论）。
4. 编辑文档优先整文件单变更块，避免零散 hunk 在审阅时被部分还原。
