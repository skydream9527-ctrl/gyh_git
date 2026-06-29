# ICE Data Workbench v3 · 设计方案

> 源仓库：`https://git.n.xiaomi.com/gongyunhe/ice-workbench`
> 决策原文：`design_decisions.md`（133 决策 + 3 全局约束）
> 整理时间：2026-05-27

---

## 1. 三大全局约束（不可妥协）

### G1 · 用户工作页面禁止虚构数据

所有 user-facing 页面（Dashboard / Workspace / Agent 详情 / Create-Task / Scheduled / Guide / Introduce）**禁止 mock、占位、硬编码示例**。例外仅限管理后台 EmptyState 演示页和 `design_v3/` 设计稿。

### G2 · 三级角色体系

`super_admin / admin / user`，权限矩阵在 `requirements/SHARED.md §2`。硬约束：

- `super_admin` 必须飞书 OAuth，密码登录返回 `SUPER_ADMIN_REQUIRES_FEISHU`
- 任何时候系统至少保留 1 个 `super_admin`
- `super_admin` 不能降级自己

### G3 · 文件优先存储（最重要的设计基石）

**文件系统是 source of truth，SQLite (`.cache/index.db`) 仅作派生索引**。任何违反此约束的代码都是 bug。

```text
agents/{agent_dir}/         # 5 内置 Agent 目录
skills/{skill_name}/        # 25 内置 Skill 目录
files/{file_name}.md        # 公共文件
users/{user_id}/
  profile.json
  settings.json
  notifications/{YYYY-MM}.jsonl
  audit/{YYYY-MM}.jsonl
  tasks/index.json
tasks/{task_id}/
  meta.json
  workspace.json
  conversations/{conv_id}.jsonl
  files/input/, output/, uploaded/
  files/.meta/{filename}.json
  collaborators.json
  experience_cards.json
  tool_calls/{conv_id}.jsonl
  scheduled.json
```

为什么这么设计：

1. **跨机搬运**——`make pack` zip → scp → `./deploy.sh --prod` 即可还原全量数据，无 dump/restore。
2. **运行时热更**——重新部署不会清空 `users/ tasks/ files/ .env`，pack 列表硬编码不含运行时数据。
3. **可审计**——文件 diff 即审计；JSONL 追加只读，避免锁竞争。
4. **可重建**——SQLite 索引启动时校验，行数与文件系统不一致就自动 `rebuild_index.py`。

实现要点：

- 路径解析全部走 `backend/app/core/storage/paths.py`，禁止内联 `os.path.join`
- 多文件写入走 `file_transaction()`：`portalocker` advisory lock + atomic backup + rollback
- 追加型数据（对话、tool calls、审计、通知）一律 `*.jsonl` 而非 `*.json`，避开整文件锁
- 写文件 + 写 SQLite 索引必须在同一个 `file_transaction` 内

---

## 2. 后端架构

### 2.1 分层

```
backend/app/
├── main.py            # FastAPI app + lifespan（启动 seed + scheduler 20s 扫描）
├── api/v1/            # 一个资源一个 router 模块（auth/tasks/agents/skills/...）
├── services/          # 业务逻辑——所有文件 I/O 必须在这层
├── core/
│   ├── storage/       # paths / jsonio / file_transaction / SQLite cache
│   ├── deps.py        # 双认证：Aegis OR JWT
│   ├── aegis.py       # X-Proxy-UserDetail RSA 验签
│   └── errors.py      # APIError + ErrorCode 枚举
├── schemas/           # Pydantic DTO
└── seed/              # 启动种子（admin / 测试用户 / bundled agents-skills）
```

**铁律**：API 层只做参数校验和响应封装，所有文件 I/O 进 `services/`。

### 2.2 双认证

`core/deps.py` 同时支持：

- `X-Proxy-UserDetail`（米盾 Aegis，RSA 多 key 轮转）
- `Authorization: Bearer <jwt>`

两路返回相同 user-dict 形状，handler 不需要分支。WebSocket 额外支持 subprotocol `["bearer", "<token>"]`（首选）和 `?token=`（legacy）。

`AEGIS_DEV_BYPASS_EMAIL` 必须配合 `X-Dev-Bypass: 1` header 才生效——确保线上误开关时不会出事。

### 2.3 LLM 网关协议路由

`services/llm_gateway.py` 按 model id 前缀路由到 4 套协议，输出统一内部事件流（`text` / `tool_use_delta` / `message_done`）：

| 前缀 | 协议端点 | 备注 |
|---|---|---|
| `ppio/pa/claude-*` | `/anthropic/v1/messages` | Anthropic native，**Claude 首选**，支持 tool_use streaming |
| `azure_openai/*` | `/v1/responses` | OpenAI Responses API（SSE） |
| `vertex_ai/*` / `xiaomi/*` 等含 `/` | `/v1/chat/completions` | OpenAI Chat Completions（best-effort） |
| 无 `/` | `ANTHROPIC_BASE_URL` | 旧 Anthropic SDK 直连（fallback） |

`MIFY_GATEWAY_*` 是首选，`ANTHROPIC_API_KEY` 是降级 fallback；两者都没配 → `/ws` 返回 `LLM_KEY_MISSING`。

### 2.4 Tool Calling 与 Agent Runtime

**5 轮 bounded ReAct loop**：`MAX_TOOL_ROUNDS=5`、`TOOL_TIMEOUT_SEC=30`。

- 主链路（流式）：`api/v1/ws.py`
- 副链路（非流式，子 agent / 后台任务）：`services/agent_runtime.run_agent_turn`

内置工具（不论哪个 Agent 都可用）：

| 工具 | 用途 |
|---|---|
| `now` / `echo` | 调试 |
| `kyuubi_query` | xiaomi-kyuubi-cli 跑 SELECT |
| `feishu_publish` / `feishu_upload_image` | 通过 `feishu` CLI 发飞书文档/图片 |
| `write_file` | 落盘到 `tasks/{tid}/files/output/` |
| `execute_python` | 沙箱 Python（仅 data-analysis agent） |

**外部 CLI 优雅降级**：缺 `kyuubi` / `feishu` 时返回 `*_NOT_CONFIGURED` 错误码，**不阻塞启动**。新加集成必须遵守此约定。

**Inflight guard**：`(task_id, conv_id)` 一次只允许一个 turn 在跑。第二条消息进来返回 `CONVERSATION_INFLIGHT`。WS 断线**不**取消 turn，只有显式 `abort` 消息才翻转 cancel event。

### 2.5 Python 沙箱（data-analysis 专用）

独立 venv `backend/.venv-sandbox/`（`make install-sandbox` 一次性 bootstrap），白名单包：`pandas / numpy / scipy / sklearn / statsmodels / prophet / ruptures / matplotlib / seaborn / pyarrow`。

强制隔离：

| 维度 | 限制 |
|---|---|
| CPU | 60s |
| 内存 | 1GB（Linux RLIMIT_AS） |
| 文件大小 | 50MB |
| 网络 | socket monkey-patched，禁出网 |
| 环境变量 | 不下传任何服务凭证 |
| 工作目录 | `<task_workspace>/files/output/` |
| 状态 | Stateless，每次 fresh process |

代码：`backend/app/services/sandbox/`。

### 2.6 v2 运行时机制（默认关）

TodoList / sub-agent / plan mode / parallel tools / compaction / background tasks 都受 `ICE_*_ENABLED` 环境变量门控。**只有 compaction 默认开**，其余默认关，保证升级时对话状态 bit-stable。

### 2.7 错误码统一

服务端**只能** `raise APIError(status, ErrorCode.X, msg)`（来自 `core/errors.py`），`main.py` 的异常处理器把 `APIError` / `StarletteHTTPException` / 未捕获 `Exception` 全部转成统一信封：

```json
{ "code": 200, "message": "...", "error_code": "...", "data": {...} }
```

**禁止**直接 `raise HTTPException`。

---

## 3. 前端架构

### 3.1 路由与懒加载

`frontend/src/App.tsx` 中 `/login` / `/introduce` / `/auth/feishu/callback` 是 eager（用户进站第一屏），其余全部 React.lazy。Admin 共享 `AdminLayout`。

### 3.2 目录结构

```
frontend/src/
├── App.tsx              # 路由入口
├── api/
│   ├── client.ts        # axios + 拦截器（401 刷新 refresh token / 错误信封解析）
│   └── endpoints.ts     # typed endpoint 常量
├── pages/
│   ├── login/ introduce/ dashboard/ workspace/ create_task/
│   ├── scheduled/ agent_detail/ guide/ auth_callback/ public_file/
│   └── admin/           # 13 个后台子页
├── components/
│   ├── chat/            # 流式对话 UI
│   ├── task/            # 任务卡 / 任务列表
│   ├── markdown/        # react-markdown + DOMPurify 统一渲染
│   ├── feedback/        # Toast / Skeleton / ErrorState / ConfirmModal
│   ├── guards/          # AuthGuard / AdminGuard
│   └── shell/           # TopNav / MobileBottomBar / InviteInbox
├── stores/              # Zustand：authStore / uiStore
├── hooks/               # useFileUpload 等
└── styles/              # tokens.css / global.css
```

路径别名：`@/` → `frontend/src/`。

### 3.3 Vite 打包策略

只把 React 核心拆出 vendor chunk，其余全打成一个 `vendor`——**故意为之**。拆 markdown/refractor 时撞到循环 ESM 依赖会导致白屏（已踩坑）。

Dev 时 Vite proxy `/api` 转发到 `:8000`（含 ws:true）。Prod 时后端直接 mount `frontend/dist/`，单端口伺服 SPA + API + WS。

### 3.4 设计 Token

v3 暖色调 + Morandi 范式色，dark / light 双模式由 CSS 变量切换。关键 token：

- `--primary` 暖琥珀 `#e8915a`（dark）/ `#c27040`（light）
- 5 范式色：雾蓝 AB / 暖金经营 / 淡紫灰度 / 灰绿数据 / 暗红波动
- 字体：Sora（标题）/ DM Sans（正文）/ JetBrains Mono（代码）
- 圆角：`--radius 12px / --radius-sm 8px / --radius-xs 6px`

响应式断点：`1100px` 隐 RightPanel，`900px` 登录页双栏 → 单栏，`800px` 隐 Sidebar。

### 3.5 行为约定

- 文件引用用 markdown link `[file.tsx:42](path/file.tsx#L42)`，**不**用 backticks
- 「重设计 UI」默认仅做视觉换肤（tokens / global / fonts），不改布局/IA/命名——**移动端适配是唯一例外**
- "原子单元是任务（task），不是笔记本"——不要把 `task_id` 重命名成 notebook 风味

---

## 4. WebSocket 协议

`/api/v1/ws/conversations/{cid}?task_id=...`

- 鉴权（按优先级）：subprotocol `["bearer", "<token>"]` → query `?token=` → Aegis proxy header
- 服务端事件：`text`、`tool_use_delta`、`message_done`、`error`、`abort_ack`
- 客户端事件：用户消息 JSON、`abort` 控制消息
- Vite proxy `ws:true`，prod 单端口直接走 `/api/v1/ws`

---

## 5. Agent 设计

### 5.1 5 个内置 Agent

| 目录 | 名称 | 范式 / 用途 |
|---|---|---|
| `data-analysis/` | 数据分析 Agent | NL→SQL + 多专家辩论，覆盖 5 业务线 |
| `general/` | 通用 Agent | 集成所有能力，开放任务专用（paradigm=null） |
| `know/` | 知识库 Agent | 飞书 KB + Mify RAG 读写 |
| `learn/` | 学习 Agent | 网页抓取 + 知识沉淀 |
| `_shared/` | 共享运行时 | runtime / llm_client / tool_registry / memory（**不是** Agent） |

### 5.2 Agent 目录约定

```text
agents/{agent_name}/
├── agent.py            # AgentDefinition 注册入口
├── agent.json          # 元数据（id / name / paradigm / model / tools / skills）
├── prompt/             # System Prompt 文件（identity.md / rules.md ...）
├── tools/              # Agent 私有 tool handler
├── skills/             # Agent 默认绑定的 SKILL.md（可选）
├── .history/           # System Prompt 修改历史 prompt-{ISO}.md（D114）
└── README.md
```

### 5.3 经验沉淀闭环（D118，待补）

工作空间右侧 ✨ 沉淀经验 → 经验卡草稿 → admin `/admin/experience-cards` 审批 → 批准后注入对应 Agent 的 system prompt → 下次对话自动生效。

### 5.4 Agent 详情双视角（D63–D70）

`/agent/:agentId`：

- 普通 user：看到能力说明、可用工具/技能、示例
- admin：额外看到 4 Tab 编辑（基础 / Skills 绑定 / 测试沙盒 / 经验卡）+ 版本历史 + 一键回滚

---

## 6. 部署与跨机搬运

### 6.1 包管理

`make pack` 输出 `ice-workbench-YYYYMMDD.zip`，**包含** `.env` + `frontend/dist`，**剔除** `.venv` / `node_modules` / `.cache` / 运行时用户数据。

### 6.2 部署模式

| 命令 | 说明 |
|---|---|
| `./deploy.sh`（无参数） | 仅安装依赖 |
| `./deploy.sh --run` | dev 双端口（前 :5173 + 后 :8000，Vite proxy） |
| `./deploy.sh --prod` | uvicorn 绑 `0.0.0.0:8000`，单端口同时伺服 SPA + API + WS |

`DATA_ROOT` 默认解析到解压目录，无需手工改 `.env`，zip 解到哪就跑到哪。

### 6.3 公网部署 checklist

1. 防火墙 `ufw allow 8000` / `firewall-cmd --add-port=8000/tcp --permanent`
2. 云厂商安全组开 TCP 8000
3. **推荐反代**：nginx 承 443 + TLS → 回源 `127.0.0.1:8000`
4. 进程常驻：systemd / pm2 / tmux（README 给了 systemd unit 模板）
5. 首次登录改 `admin` 密码 + 轮换 `ICE_SECRET_KEY`（≥32 字节）+ `MIFY_GATEWAY_API_KEY`

### 6.4 热更原则（重要）

任何在线机器再次部署时**必须保留**：`users/` / `tasks/` / `files/` / `backend/.venv/` / `.env`。`make pack` 的 include 列表不能扩到运行时数据；新加部署步骤不能 wipe 这些目录。

---

## 7. 关键扩展点

### 7.1 加一个新 Agent

1. 在 `agents/<name>/` 建目录、写 `agent.json` 和 `prompt/identity.md`
2. 私有工具放 `agents/<name>/tools/`，注册到 `tool_runner`
3. 重启后 `/admin/agents` 自动发现
4. 普通用户的 `/dashboard` 范式卡通过 `agent.json` 的 `paradigm` 字段路由

### 7.2 加一个新 Skill

1. `skills/<name>/SKILL.md` 写技能描述 + 输入 schema
2. 在 `/admin/skills` 上传 / 编辑 / 沙盒 test-run
3. 在 Agent 编辑页 Skills Tab 绑定

### 7.3 加一个新模型

1. `.env` 增加 `MIFY_GATEWAY_*` 配置
2. 若需要新协议——在 `services/llm_gateway.py` 加前缀分支即可（4 套协议都已抽象成统一事件流）

### 7.4 加一个外部 CLI 工具

1. `tool_runner` 注册 handler
2. **必须**实现"缺 CLI 时返回 `*_NOT_INSTALLED`"的降级路径，**禁止**让启动崩溃

---

## 8. 设计决策导航

按主题组分布在 `design_decisions.md` 中：

| 决策段 | 主题 |
|---|---|
| D1–D10 | 技术栈 / 全局约束 |
| D63–D70 | Agent 详情页双视角 |
| D71–D76 | 3-Step 创建任务工坊 |
| D77–D82 | 定时任务 cron 调度 + 历史回放 |
| D85–D87 | 三级角色与 super_admin 飞书强制 |
| D90–D95 | 使用指南页 |
| D96–D100 | 产品介绍页 |
| D113 | admin Agent 编辑 4 Tab |
| D114 | System Prompt 版本历史 |
| D115 | 范式预设 |
| D118 | 经验卡片审批闭环 |
| D122 | 公共任务审核流 |
| D125–D128 | LLM 单价 / 月度预算 / SQL CSV 导出 |
| D134–D139 | G3 文件优先存储 |
| G1 / G2 / G3 | 三大全局约束 |

详细操作步骤见 [`ice-workbench-usage-guide.md`](./ice-workbench-usage-guide.md)。
