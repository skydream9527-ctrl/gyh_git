# ICE Data Workbench v3 · 使用指南

> 源仓库：`https://git.n.xiaomi.com/gongyunhe/ice-workbench`
> 同目录代码副本：[`../project/`](../project/)
> 整理时间：2026-05-27

---

## 一、5 分钟快速启动（本地）

### 前置依赖

- Python ≥ 3.10
- Node ≥ 18
- 可选：`xiaomi-kyuubi-cli`（SQL 工具）、`feishu` CLI（飞书工具）——缺失时相关工具返回 `*_NOT_CONFIGURED`，**不阻塞启动**

### 一行命令

```bash
cd ice-workbench
./deploy.sh --run
```

打开 `http://localhost:5173`，默认账号 `admin / admin123`。

### 分步等价

```bash
make install     # backend pip + frontend npm
make dev         # backend :8000 + frontend :5173（Vite proxy /api → 8000）
```

> `.env` 已随项目分发，包含 mify 网关凭证，可直接跑通 8 个模型对话。**生产前必须轮换** `ICE_SECRET_KEY` 与 `MIFY_GATEWAY_API_KEY`。

---

## 二、跨机部署

### 源机器打包

```bash
make pack
# 输出 ice-workbench-YYYYMMDD.zip
# 包含：源码 + frontend/dist 预构建 + .env
# 剔除：.venv / node_modules / .cache / 运行时用户数据
```

### 目标机器解压并跑

```bash
scp ice-workbench-*.zip user@target:~
ssh user@target

unzip ice-workbench-*.zip -d ice-workbench
cd ice-workbench

./deploy.sh --prod   # 生产模式：单端口 0.0.0.0:8000 同时伺服 SPA + API + WS
# 或
./deploy.sh --run    # dev 模式：双端口 :5173 + :8000
```

`deploy.sh` 会：

1. 校验 Python 3.10+ / Node 18+
2. 创建 backend `.venv` 并 pip install，跑 pytest 自检
3. `npm install` + `tsc` typecheck
4. `--prod` 时按需构建 `frontend/dist/`（zip 已带可跳过），用 uvicorn 起 `0.0.0.0:8000`
5. `--run` 走 dev 双端口；不带参数只装依赖

> **DATA_ROOT 自适应**：默认解析到解压目录，跨机搬运无需手工改 `.env`。

### Linux 公网部署 checklist

```bash
unzip ice-workbench-*.zip -d /opt/ice-workbench
cd /opt/ice-workbench

# 可选：改默认端口
export ICE_BIND_HOST=0.0.0.0
export ICE_BIND_PORT=8000

./deploy.sh --prod
# 或：make prod
```

| 步骤 | 命令 |
|---|---|
| 防火墙 | `sudo ufw allow 8000` 或 `firewall-cmd --add-port=8000/tcp --permanent` |
| 云安全组 | 控制台开 TCP 8000 入站 |
| 反代（推荐） | nginx 443 + TLS → `127.0.0.1:8000` |
| 进程常驻 | systemd / pm2 / tmux 任选（README 有 systemd unit 模板） |
| 安全 | 首次登录改 `admin` 密码；轮换 `ICE_SECRET_KEY` ≥32 字节、`MIFY_GATEWAY_API_KEY` |

---

## 三、常用 Make 命令

```bash
make install           # backend pip + frontend npm
make install-sandbox   # bootstrap data-analysis Python 沙箱 venv
make dev               # backend :8000 + frontend :5173（仅 localhost）
make backend           # 仅后端
make frontend          # 仅前端
make test              # cd backend && pytest -q
make seed              # 一次性种子（admin / 测试用户）
make fmt               # ruff --fix + eslint --fix
make prod              # build dist + uvicorn 0.0.0.0:$PROD_PORT 单端口
make pack              # 输出 ice-workbench-YYYYMMDD.zip
make pack-clean        # pack 前先 reset-data（干净交付）
make reset-data        # 清空 .cache / users/<uuid> / tasks/<uuid>，保留 seed
```

> ⚠️ **永远不要在 LAN 可达 IP 上跑 `make dev`**——Vite dev server 会暴露完整 `/src` 源码 + sourcemap，且无安全 header。多设备测试请用 `make prod`。

### 单测试 & 工具

```bash
# 跑单条用例
cd backend && . .venv/bin/activate && pytest tests/test_auth.py::test_login_password -q

# 前端类型检查
cd frontend && npx tsc --noEmit

# 重建 SQLite 索引（索引坏了的兜底）
cd backend && . .venv/bin/activate && python scripts/rebuild_index.py
```

---

## 四、首次使用（user 视角）

### 4.1 登录

- 默认 `admin / admin123`（首启自动种子化）
- 或飞书 OAuth → `/auth/feishu/callback`

### 4.2 创建任务（3-Step 工坊）

`/create-task`：

1. **Step 1**：选范式（AB 实验 / 经营分析 / 版本灰度 / 数据分析 / 波动归因 / 通用）
2. **Step 2**：填任务名、描述、附件
3. **Step 3**：选 Agent + 模型，确认后跳 `/workspace/:taskId`

### 4.3 工作空间

`/workspace/:taskId` 三栏：

- **左栏**：任务列表 + 切换
- **中栏**：流式对话（最多 5 轮 Tool Calling 自动循环）
- **右栏**：任务文件 / ✨ 沉淀经验 / 🔗 分享

> 单个对话流转 `(task_id, conv_id)`。同一对话只能有一个 turn 在跑——再发消息会返回 `CONVERSATION_INFLIGHT`。

### 4.4 定时任务

`/scheduled-tasks`：填 cron 表达式 → 后端 scheduler 每 20 秒扫描自动触发，历史回放可看每次跑的对话。

### 4.5 沉淀经验

工作空间右栏 ✨ → 草稿 → 提交 → admin 审批（`/admin/experience-cards`）→ 批准后注入 Agent 的 system prompt → 下次对话生效。

---

## 五、admin 后台（13 个子页）

| 路径 | 功能 |
|---|---|
| `/admin` | 概览 + Stats / Alerts / 排行 |
| `/admin/usage` | 用量与成本（5 Tab + 月度预算 + CSV） |
| `/admin/sql-audit` | SQL 审计（3 级分类 + CSV） |
| `/admin/audit` | 操作审计日志 |
| `/admin/review-center` | 审核中心聚合（待办计数） |
| `/admin/experience-cards` | 经验卡片审批 |
| `/admin/public-tasks` | 公共任务审核 |
| `/admin/templates` | 任务模板审核 |
| `/admin/agents` | Agent 列表 |
| `/admin/agents/:id` | Agent 编辑（4 Tab + 版本历史 + 一键回滚 + 沙盒） |
| `/admin/skills` | Skill CRUD + JSON schema 验证 + 沙盒 test-run |
| `/admin/knowledge-bases` | KB CRUD + 飞书 wiki 同步 + 同步日志 |
| `/admin/files` | 公共文件上传 / 编辑 / 置顶 |
| `/admin/users` | 用户管理（角色编辑限 super_admin） |
| `/admin/settings` | 系统设置（开关 / LLM / 参数 / 公告） |

### 角色矩阵速查

| 操作 | super_admin | admin | user |
|---|:-:|:-:|:-:|
| 修改任意 user 角色 / 删除 user | ✅ | ❌ | ❌ |
| 系统配置 / 单价 / 月度预算 | ✅ | ❌ | ❌ |
| Agent / Skill / KB / 公告 / 模板 / 经验卡 / 公共任务审核 | ✅ | ✅ | ❌ |
| 创建任务 / 对话 / 上传文件 / 浏览公共区 | ✅ | ✅ | ✅ |

> super_admin 必须飞书 OAuth；密码登录返回 `SUPER_ADMIN_REQUIRES_FEISHU`。super_admin 不能降级自己；系统至少保留 1 个 super_admin。

---

## 六、飞书 OAuth 接入

### 6.1 步骤

1. 飞书开放平台（标准：`open.feishu.cn/app`，小米走内部入口）创建企业自建网页应用
2. 加权限作用域：`contact:user.id` `contact:user.base` `contact:user.email`
3. 把回调 URL 加白名单：`http://你的域:5173/auth/feishu/callback`（线上用线上域名）
4. `.env` 填：

   ```ini
   FEISHU_APP_ID=cli_xxxxxxxxxxxx
   FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxx
   FEISHU_HOST=https://open.feishu.cn       # 小米内部改内部域名
   FEISHU_REDIRECT_URI=http://10.x.x.x:5173/auth/feishu/callback
   ```

5. 重启后端，登录页"使用小米账号登录"按钮变可点

### 6.2 自动建号开关

`/admin/settings`（仅 super_admin）：

| toggle | 默认 | 行为 |
|---|---|---|
| `enable_feishu_auto_register` | `true` | 飞书首次登录自动建 `user` 账号 |
| `enable_feishu_strict_whitelist` | `true` | 严格白名单：未在 users 表的飞书账号被拒（与 auto_register 互斥） |

### 6.3 流程

```
点 [飞书登录]
  → 跳到飞书授权
  → 飞书 302 → /auth/feishu/callback?code=...&state=...
  → SPA POST /api/v1/auth/feishu/oauth/callback
  → 后端 code → user_access_token → user_info
  → 查 email/feishu_user_id：
      · 找到 → auto-bind + 签 JWT
      · 没找到 + auto_register=true → 建 user 账号 + 签 JWT
      · 没找到 + auto_register=false → 403 FEISHU_ACCOUNT_NOT_WHITELISTED
```

> **兜底**：用户拒绝授权 email 时，后端用 `feishu-{open_id前12位}@auto.local` 合成 email，不影响登录。后续在 admin 后台补 email，下次飞书登录会按 email 自动合并账号。

---

## 七、模型网关配置

`mify` 网关按 model id 前缀路由 4 套协议：

| 前缀 | 协议 | 备注 |
|---|---|---|
| `ppio/pa/claude-*` | Anthropic native（`/anthropic/v1/messages`） | **Claude 首选**，支持 tool_use streaming |
| `azure_openai/*` | OpenAI Responses API（`/v1/responses`） | SSE |
| `vertex_ai/*` / `xiaomi/*` 等 | OpenAI Chat Completions（`/v1/chat/completions`） | best-effort |
| 无 `/` | Legacy Anthropic SDK | `ANTHROPIC_BASE_URL` fallback |

### 配置优先级

1. `MIFY_GATEWAY_BASE_URL` + `MIFY_GATEWAY_API_KEY`（首选）
2. `ANTHROPIC_API_KEY`（fallback）
3. 都缺 → `/ws` 返回 `LLM_KEY_MISSING`

---

## 八、环境变量速查

详见 `.env.example`。关键项：

| 变量 | 必需 | 说明 |
|---|:-:|---|
| `ICE_SECRET_KEY` | ✅ | JWT 签名密钥（≥32 字节） |
| `MIFY_GATEWAY_BASE_URL` + `MIFY_GATEWAY_API_KEY` | ⚠ | mify 模型网关，支持 8 个预设 |
| `ANTHROPIC_API_KEY` | — | 旧版回退，仅 mify 未配置时启用 |
| `FEISHU_APP_ID` / `FEISHU_APP_SECRET` | ⚠ | 不填时飞书按钮返回 `FEISHU_NOT_CONFIGURED` |
| `KYUUBI_HOST` 等 | ⚠ | 不填时 SQL skill 返回 `KYUUBI_NOT_CONFIGURED` |
| `ICE_BIND_HOST` / `ICE_BIND_PORT` | — | 生产模式绑定地址 / 端口 |
| `ICE_*_ENABLED` | — | v2 运行时 feature gate（TodoList / sub-agent / plan-mode / parallel-tools / bg-tasks） |
| `AEGIS_DEV_BYPASS_EMAIL` | — | 仅配合 `X-Dev-Bypass: 1` 生效 |

---

## 九、可选 CLI 工具

```bash
pipx install xiaomi-kyuubi-cli   # Kyuubi SQL 网关
# feishu CLI：按内部文档安装
```

两者缺失时相关工具返回 `*_NOT_CONFIGURED`，不阻塞启动。

---

## 十、常见问题

### Q1：SQLite 索引坏了

```bash
cd backend && . .venv/bin/activate && python scripts/rebuild_index.py
```

启动时框架会自动校验行数，发现不一致也会自动重建。

### Q2：端口冲突

- 后端：改 `Makefile` 中 `--port 8000`
- 前端：改 `frontend/vite.config.ts` 中 `server.port`

### Q3：飞书登录按钮灰

`.env` 没填 `FEISHU_APP_ID/SECRET` 或飞书后台没加回调 URL。补全后重启后端即可。

### Q4：WS 偶发 `STREAM_INTERRUPTED`

通常是 ws ping/pong 太紧。Makefile 默认 `--ws-ping-interval 30 --ws-ping-timeout 60`；自定义启动时也要带这俩参数。

### Q5：再次部署会不会清空我的数据

不会。`make pack` 的 include 列表硬编码不含 `users/ tasks/ files/ backend/.venv/ .env`；`./deploy.sh --prod` 解压不会覆盖这些目录。**热更原则**：任何在线机器再次部署必须保留这些路径。

### Q6：admin 改了密码忘了

```bash
make seed   # 重新跑种子（不会覆盖已有数据，但 admin 默认密码会重置）
```

### Q7：模型不响应

依次排查：

1. `MIFY_GATEWAY_*` 是否填全
2. mify gateway 是否可达（`curl $MIFY_GATEWAY_BASE_URL/health`）
3. model id 前缀是否落在 4 套协议任一区间（见第 7 节）
4. `/admin/settings` 检查 `llm_enabled` 开关

### Q8：data-analysis agent 跑 Python 报"沙箱未初始化"

```bash
make install-sandbox   # 一次性 bootstrap backend/.venv-sandbox/
```

---

## 十一、源码导航

代码副本完整保存在 [`../project/`](../project/)，关键路径：

| 路径 | 说明 |
|---|---|
| `design_decisions.md` | 133 决策 + 3 全局约束 |
| `requirements/SHARED.md` | 全局约束 / 设计 token / 协议规范 |
| `requirements/BACKEND.md` | 后端需求 |
| `requirements/FRONTEND.md` | 前端需求 |
| `reference/route-map.md` | 23 路由 ↔ 决策映射 |
| `reference/api-map.md` | API ↔ 决策映射 |
| `backend/app/` | FastAPI 应用 |
| `frontend/src/` | React 应用 |
| `agents/` | 5 内置 Agent |
| `skills/` | 内置 Skills |
| `design_v3/` | 14 份 v3 HTML 设计稿 |

延伸阅读：[`ice-workbench-introduction.md`](./ice-workbench-introduction.md)、[`ice-workbench-design.md`](./ice-workbench-design.md)。
