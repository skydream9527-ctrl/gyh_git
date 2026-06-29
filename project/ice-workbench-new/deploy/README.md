# 服务端部署说明（Server Deployment）

本目录是**服务端部署时需要关注和执行的事项清单**。面向：把 ICE Data Workbench 部署/升级到米盾内网或自有服务器的同学。

> 三条部署路径，按场景选：
> - **裸机单端口（推荐，内网）**：`./deploy.sh --prod`（本文件主讲）
> - **Docker 自托管**：见 [`../docs/SELF_HOSTING.md`](../docs/SELF_HOSTING.md)
> - **本地开发**：`make dev`（仅 localhost，切勿暴露到公网）
>
> 架构约束与设计决策见 [`../CLAUDE.md`](../CLAUDE.md) 和 [`../design_decisions.md`](../design_decisions.md)，部署前建议先读「G3 文件优先存储」一节。

---

## 0. TL;DR — 一次干净部署

```bash
# 1. 准备 .env（必改 3 项，见 §2）
cp .env.example .env && $EDITOR .env

# 2. 安装依赖 + 跑测试 + 构建前端 + 单端口启动（0.0.0.0:8000）
./deploy.sh --prod

# 3. 取初始 admin 密码（首启后随机生成）
cat .cache/initial_admin_password.txt

# 4. 健康检查
curl -fs http://<服务器IP>:8000/api/v1/health
```

---

## 1. 环境要求

| 组件 | 版本 | 说明 |
|------|------|------|
| Python | ≥ 3.10 | `deploy.sh` 会校验，低于 3.10 直接报错 |
| Node.js | ≥ 18 | 构建前端 `frontend/dist` |
| 内存 | ≥ 4 GB | 首次装 `prophet/scipy` 编译会短暂吃满 |
| 磁盘 | ≥ 10 GB | 依赖 + 运行时数据 |

可选外部 CLI（**缺失不阻塞启动**，对应工具会返回 `*_NOT_CONFIGURED` / `*_NOT_INSTALLED`）：
- `kyuubi`（SQL 查询）：`pipx install xiaomi-kyuubi-cli`
- `feishu`（飞书发布）：按内部文档安装

---

## 2. 必须配置的环境变量（`.env`）

部署前**至少**确认这几项，否则服务起不来或登录不了：

| 变量 | 必填 | 说明 |
|------|:---:|------|
| `ICE_SECRET_KEY` | ✅ | JWT 签名密钥。生成：`openssl rand -hex 32`。**绝不可用默认值上线** |
| `MIFY_GATEWAY_API_KEY` | ✅(二选一) | LLM 网关 key；为空则回退 `ANTHROPIC_API_KEY` |
| `ANTHROPIC_API_KEY` | ✅(二选一) | 两个都空 → `/ws` 返回 `LLM_KEY_MISSING`，无法对话 |
| `AEGIS_ENABLED` | 生产=true | 开启米盾代理鉴权（`X-Proxy-UserDetail`） |
| `AEGIS_PUBLIC_KEY` | AEGIS 开时必填 | 米盾控制台「安全代理公钥」，支持逗号分隔多 key 轮转 |
| `AEGIS_ADMIN_EMAILS` | 建议 | 逗号分隔，授予 super_admin |
| `AEGIS_DEV_BYPASS_EMAIL` | **必须为空** | 仅本地开发用；staging/prod 留空，否则鉴权被绕过 |
| `ICE_CORS_ORIGINS` | 建议 | 生产填实际访问域名/IP |

> ⚠️ **super_admin 必须走飞书 OAuth 登录**（密码登录会返回 `SUPER_ADMIN_REQUIRES_FEISHU`）。生产环境需正确配置 `FEISHU_APP_ID` / `FEISHU_APP_SECRET` / `FEISHU_REDIRECT_URI`。

其余可选项（Kyuubi / Feishu / 语音 / 沙箱 / Data Platform MCP）见 [`.env.example`](../.env.example) 内联注释。

---

## 3. 部署步骤（裸机单端口）

`./deploy.sh --prod` 实际做的事（可对照源码 [`../deploy.sh`](../deploy.sh)）：

1. 校验 Python ≥ 3.10、Node ≥ 18、npm；缺 kyuubi/feishu 仅告警
2. `.env` 不存在则从 `.env.example` 复制（**复制后务必去改密钥**）
3. 建 `backend/.venv`，`pip install -e ".[dev]"`
4. **跑一遍 pytest**（失败仅告警，不阻塞——但生产部署前应确认全绿）
5. 前端 `npm install` + `tsc --noEmit` 类型检查
6. `npm run build` 产出 `frontend/dist`
7. `uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 --ws-ping-interval 30 --ws-ping-timeout 60`

单端口同时伺服 **SPA + API + WebSocket**，无需单独部署前端。

可调端口/绑定/worker：

```bash
ICE_BIND_PORT=8080 ICE_BIND_HOST=0.0.0.0 ICE_WORKERS=4 ./deploy.sh --prod
```

> WebSocket ping/pong 用 30/60s（不是 uvicorn 默认 20/20）。长会话/多会话并发时 event loop 偶发被同步 IO 卡 >20s 会被误判超时关连接 → 前端 `STREAM_INTERRUPTED`。改这个值要同步 `Makefile` / `deploy.sh` / `Dockerfile` 三处。

### data-analysis agent 的 Python 沙箱（按需）

`execute_python` 工具需要独立沙箱 venv，**首次部署单独跑一次**：

```bash
make install-sandbox   # 创建 backend/.venv-sandbox
```

不装则 `execute_python` 不可用（其它功能不受影响）。沙箱内存/超时上限见 `.env` 的 `ICE_PYTHON_SANDBOX_*`。

---

## 4. ⚠️ 热更新：升级时绝不能丢的数据（G3 文件优先）

**文件系统是唯一事实源，SQLite 只是派生索引。** 在已上线机器上重新部署时，必须保留以下目录/文件，否则用户数据、历史任务、密钥全丢：

| 路径 | 内容 | 丢失后果 |
|------|------|---------|
| `.env` | 所有密钥与配置 | 密钥全部要重发 |
| `users/` | 每用户账号/偏好/收藏 | 用户要重新注册 |
| `tasks/` | 会话历史、产物、附件 | 历史任务全没 |
| `files/` | 用户上传文件 | 文件全没 |
| `agents/*/prompt/cards.md` | 用户编辑的 prompt 卡片 | 自定义 prompt 丢失 |
| `skills/` | 用户上传的 skill 包 | 自定义 skill 全没 |
| `.cache/` | SQLite 索引、scheduler 锁、初始管理员密码 | 可由 `rebuild_index.py` 重建，首启较慢 |
| `backend/.venv/` | 后端虚拟环境 | 需重装依赖（耗时） |

升级前先备份：

```bash
tar czf backup-$(date +%F).tgz .env users tasks files agents skills .cache
```

> `make pack` 打出的便携 zip **故意不包含**上述运行时数据（只含源码 + `.env.example` + dist；**不含 `.env`**，密钥不随包扩散）。不要把运行时数据加进 pack 的 include 列表，也不要在部署脚本里 `rm -rf` 这些目录。

后端 `lifespan` 启动时会自动：① `bootstrap()` 种子目录/admin/内置 agent；② SQLite schema 检查/升级；③ 索引行数不一致则自动重建；④ 启动 scheduler。所以误删 `.cache/` 重启即可恢复索引。

---

## 5. 部署后验证

```bash
# 健康检查
curl -fs http://<服务器IP>:8000/api/v1/health

# 路由数（deploy.sh 已打印）/ 进程
ps aux | grep uvicorn
```

公网/局域网可达检查：
1. 防火墙放行端口：`sudo ufw allow 8000`（Debian/Ubuntu）或 firewalld
2. 云服务器安全组 / VPC 开放 TCP 入站
3. （可选）nginx 反向代理 + HTTPS——注意 WebSocket 需 `proxy_set_header Upgrade`/`Connection` 透传，且 idle timeout ≥ 60s

登录验证：
- 内网米盾环境：经 Aegis 代理访问，首个 `AEGIS_ADMIN_EMAILS` 用户即 super_admin
- 非米盾环境：用 `admin` + `.cache/initial_admin_password.txt` 里的随机密码登录，**首次登录立即改密**

---

## 6. Agent 运行时特性开关（灰度）

所有 v2 机制默认**关**（升级零行为变化），仅 `ICE_COMPACTION_ENABLED` 默认开。按环境逐个灰度，**改完需重启服务**生效：

| 开关 | 默认 | 作用 |
|------|:---:|------|
| `ICE_COMPACTION_ENABLED` | on | 长上下文摘要压缩 |
| `ICE_TODO_ENABLED` | off | Agent 自维护 TodoList |
| `ICE_SUBAGENT_ENABLED` | off | `spawn_subagent` 派单子 agent |
| `ICE_PLAN_MODE_ENABLED` | off | Plan / ExitPlan 审批流 |
| `ICE_PARALLEL_TOOLS_ENABLED` | off | 一轮并行执行多个只读工具 |
| `ICE_BG_TASK_ENABLED` | off | `run_background` 后台任务 |
| **`ICE_AGENT_KERNEL_ENABLED`** | **off** | **用户对话走统一 agent_kernel（与子 agent 同一套 ReAct 循环）** |

> 🚩 `ICE_AGENT_KERNEL_ENABLED` 是本次重构（统一 agent_kernel）的总开关。子 agent / 后台 / 调度器**已经**在走内核；这个开关只控制**用户对话（ws）**这条路。打开前**必须**先按 [`STAGING_CHECKLIST_agent_kernel.md`](STAGING_CHECKLIST_agent_kernel.md) 在 staging 跑一遍验证，因为 ws 流式路径目前没有自动化集成测试。

---

## 7. 常见问题排查

| 现象 | 可能原因 / 处理 |
|------|----------------|
| `/ws` 返回 `LLM_KEY_MISSING` | `MIFY_GATEWAY_API_KEY` 和 `ANTHROPIC_API_KEY` 都为空 |
| 登录提示 `SUPER_ADMIN_REQUIRES_FEISHU` | super_admin 只能飞书 OAuth；检查 `FEISHU_*` 配置 |
| 前端白屏 | `frontend/dist` 没构建（跑 `make prod-build`）或 nginx 没把 `/` 指到后端 |
| 对话中途 `STREAM_INTERRUPTED` | 反代 idle timeout 太短 / ws ping 阈值；确认反代 ≥60s 且 uvicorn ws-ping 30/60 |
| `kyuubi_query` 返回 `KYUUBI_NOT_CONFIGURED` | 部署机没装 kyuubi CLI 或 `KYUUBI_*` 没配 |
| `execute_python` 不可用 | 没跑 `make install-sandbox` |
| 索引和文件对不上 | 重启服务自动重建，或手动 `python scripts/rebuild_index.py` |

---

## 目录内文件

- [`README.md`](README.md) — 本文件，服务端部署总览
- [`STAGING_CHECKLIST_agent_kernel.md`](STAGING_CHECKLIST_agent_kernel.md) — agent_kernel 迁移上线前的 staging 验证清单
