# 自托管部署指南（Docker Compose）

ICE Data Workbench 容器化部署路径。适合：跨机器迁移、给外部用户/客户提供自托管样板、升级流程标准化。

> 想跑米盾内网部署、不要容器？继续用 [`./deploy.sh`](../deploy.sh)。Docker 路径不替代它，是补充。

---

## 系统要求

- Docker 24+ 和 Docker Compose v2（`docker compose`，不是老的 `docker-compose`）
- ≥ 4 GB RAM（prophet/scipy 编译时短暂吃满）
- ≥ 10 GB 磁盘空间（镜像约 1.5–2 GB + 运行时数据）

```bash
docker --version && docker compose version
```

---

## 首次部署

```bash
git clone <repo-url> ice-workbench && cd ice-workbench

# 1. 准备 .env —— 必改两项：
#    ICE_SECRET_KEY      用 openssl rand -hex 32 生成
#    MIFY_GATEWAY_API_KEY 或 ANTHROPIC_API_KEY  二选一，否则 /ws 返回 LLM_KEY_MISSING
cp .env.example .env
$EDITOR .env

# 2. 起容器（首次 build 5–10 分钟：npm install + prophet 编译）
docker compose up -d --build

# 3. 等 30 秒让 seed bootstrap 跑完，然后取初始 admin 密码
docker exec ice-workbench cat /app/.cache/initial_admin_password.txt

# 4. 浏览器访问
#    http://localhost:8000        本机
#    http://<server-ip>:8000      局域网/公网（先放行防火墙 8000 端口）
```

健康检查：

```bash
curl -fs http://localhost:8000/api/v1/health
docker compose ps   # STATUS 应该是 healthy
```

---

## 数据持久化（必读）

`docker-compose.yml` 把 6 个目录 + `.env` bind mount 到宿主当前目录。**docker compose down 不会删；docker compose down -v 也不会删**（`-v` 只对 named volume 生效，我们用的是 bind mount）。但你 `rm -rf` 这些目录，数据就真没了。

| 宿主目录 | 容器内 | 内容 | 不能丢的理由 |
|---------|--------|-----|------------|
| `users/` | `/app/users` | 每用户 uuid 子目录：账号、偏好、收藏 | 丢 = 所有用户重新注册 |
| `tasks/` | `/app/tasks` | 每任务 uuid 子目录：会话历史、产物、附件 | 丢 = 历史任务全没 |
| `files/` | `/app/files` | 用户上传的文件 | 丢 = 文件全没 |
| `agents/` | `/app/agents` | 内置 agent 定义 + 用户编辑的 prompt（`*/prompt/cards.md`） | 丢用户编辑的 prompt 卡片就没了 |
| `skills/` | `/app/skills` | 用户上传 skill 包 | 丢 = 自定义 skill 全没 |
| `.cache/` | `/app/.cache` | SQLite 索引 `index.db`、scheduler leader lock、初始管理员密码 | 可由 `rebuild_index.py` 重建，但首启动较慢 |
| `.env` | `/app/.env`（只读） | 所有密钥 + 配置 | 丢 = 所有密钥要重发 |

> 💡 启动时如果 `.cache/index.db` 缺失或与文件系统行数不一致，后端会自动重建索引。所以即使误删 `.cache/`，重启容器也能恢复。

---

## 升级流程

```bash
# 1. 先备份（强烈推荐）
tar czf backup-$(date +%F).tgz .env users tasks files agents skills .cache

# 2. 拉新代码
git pull

# 3. 重建镜像 + 滚动更新（迁移在后端 lifespan 自动跑）
docker compose up -d --build

# 等价 make 命令：
make docker-upgrade
```

后端启动时（[backend/app/main.py:216-228](../backend/app/main.py#L216-L228)）会自动跑：

1. `bootstrap()` —— 种子目录 + admin 用户 + 内置 agent
2. `db.init()` —— SQLite schema 检查 / 必要时升级
3. 索引一致性检查 —— 行数不匹配则触发 reindex
4. `scheduler_svc.start_loop()` —— 定时任务 leader 选举 + scan loop

**跨大版本（含 schema 改动）需手动 reindex**：

```bash
docker exec ice-workbench python /app/backend/scripts/rebuild_index.py
```

---

## 回滚

升级前先 tag 旧镜像：

```bash
# 升级前
docker tag ice-workbench:latest ice-workbench:rollback

# 滚回
docker compose down
docker tag ice-workbench:rollback ice-workbench:latest
docker compose up -d
```

bind-mount 的运行时数据保持不动 —— 滚回的同时数据延续。⚠ 但若新版本写过 schema 不向后兼容的字段，滚回后可能读不出，这种情况要从备份恢复 `.cache/` 和 `users/`/`tasks/`。

---

## 常用运维操作

| 操作 | 命令 |
|------|------|
| 查日志 | `docker compose logs -f` 或 `make docker-logs` |
| 进容器 | `docker exec -it ice-workbench bash` |
| 重启 | `docker compose restart` |
| 停止 | `make docker-down`（数据保留） |
| 清理运行时数据 | `docker exec ice-workbench make reset-data` 然后 `docker compose restart` |
| 重建索引 | `docker exec ice-workbench python /app/backend/scripts/rebuild_index.py` |
| 取初始 admin 密码 | `docker exec ice-workbench cat /app/.cache/initial_admin_password.txt` |

---

## 安装可选 CLI 工具

镜像里默认尝试装 `xiaomi-kyuubi-cli`（公网 PyPI），失败不阻塞 build。若失败或你需要自定义版本：

### 方法 A：进容器临时装（重建镜像后失效）

```bash
docker exec ice-workbench pip install xiaomi-kyuubi-cli
docker compose restart
```

### 方法 B：继承我们的镜像写自己的 Dockerfile（推荐）

```dockerfile
FROM ice-workbench:latest
RUN pip install --index-url https://your-internal-pypi/simple/ xiaomi-kyuubi-cli
```

### feishu CLI（内部产物，不会上 PyPI）

宿主机装好 `feishu` 二进制后，在 `docker-compose.yml` 加一行 bind mount：

```yaml
volumes:
  - /usr/local/bin/feishu:/usr/local/bin/feishu:ro
```

CLI 缺失时 `feishu_publish` 工具会返回 `FEISHU_CLI_NOT_INSTALLED`，不会让后端崩。

---

## 故障排查

| 症状 | 原因 / 排查 |
|------|------------|
| 容器起来就 exit | `docker compose logs ice-workbench`，最常见是 `ICE_SECRET_KEY` 没改 → 后端拒绝启动 |
| Healthcheck `unhealthy` 30s 内 | 正常。首次启动 seed bootstrap 慢，`start_period: 30s` 给了缓冲 |
| Healthcheck 持续 `unhealthy` | 看日志，可能 LLM key 没配（`/ws` 返回 LLM_KEY_MISSING 但 `/health` 应该还能 200）。`curl localhost:8000/api/v1/health` 直接试 |
| 浏览器空白页 | 检查 `frontend/dist` 是否在镜像里：`docker exec ice-workbench ls /app/frontend/dist`。没有就是 build 阶段挂了，重 build |
| 前端 hash 资源 404 | index.html 缓存了旧 hash。后端已经给 index.html 加了 `Cache-Control: no-cache`，刷新即可 |
| WebSocket 频繁断开 | 看是不是反向代理（nginx）的 timeout 过短。后端 ws ping/pong 已设 30/60s |
| `kyuubi_query` 返回 KYUUBI_NOT_CONFIGURED | CLI 未装，见上节"安装可选 CLI" |
| 多实例 / 多 worker 数据竞争 | 后端 leader-lock 已保证单实例跑 scheduler，无需手动协调 |

---

## 不在 Docker 部署支持范围

以下场景请用其他路径：

- **HTTPS / 反向代理 / 域名** —— 用户自己 nginx + certbot，把 `:8000` 反代到 `https://xxx`。我们只暴露明文 HTTP。
- **Kubernetes / 多实例** —— 小团队场景不需要。容器内 `--workers 2` 已够大部分负载（按 [Makefile L10-12](../Makefile#L10-L12) 注释，scheduler/WS inflight 已加文件锁，多 worker 安全）。
- **米盾 SSO（Aegis）** —— 需要内部网络环境。容器自托管默认走密码登录，`AEGIS_ENABLED=false` 是 Docker 部署的隐含前提。
- **使用量统计 / token 计费看板** —— 我们目前没有 usage tracking。

---

## 镜像内部结构（供 docker exec 排查参考）

```
/app
├── backend/
│   ├── app/                     # FastAPI 后端
│   ├── pyproject.toml
│   ├── requirements.sandbox.txt
│   ├── scripts/
│   │   ├── bootstrap_sandbox_venv.sh
│   │   └── rebuild_index.py
│   └── .venv-sandbox/           # ← 沙盒 venv（execute_python 工具用，prophet/pandas/scipy）
├── frontend/dist/               # ← 前端 build 产出（main.py 自动 mount /assets）
├── agents/                      # ← bind mount 覆盖（保留用户编辑的 prompt）
├── skills/                      # ← bind mount 覆盖
├── users/                       # ← bind mount
├── tasks/                       # ← bind mount
├── files/                       # ← bind mount
├── .cache/                      # ← bind mount
├── .env                         # ← bind mount（只读）
└── Makefile                     # docker exec ... make reset-data 用
```

后端 WORKDIR 是 `/app/backend`，所以 `uvicorn app.main:app` 找到的就是 `/app/backend/app/main.py`。
