# syntax=docker/dockerfile:1.6
# ICE Data Workbench — 自托管镜像（单端口同时伺服 SPA + API + WS）
# 构建：docker compose build
# 详细说明见 docs/SELF_HOSTING.md

# --------------------------------------------------------------------
# Stage 1: 前端 build（仅产出 dist，不入运行时镜像）
# --------------------------------------------------------------------
FROM node:20-alpine AS frontend-builder

WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund

COPY frontend/ ./
RUN npm run build
# → /app/dist 产物（main.py L407 期望挂载在 /app/frontend/dist）


# --------------------------------------------------------------------
# Stage 2: 运行时镜像（python + 后端 + 前端 dist + 沙盒 venv）
# --------------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

# build-essential：prophet/scipy 编译期需要
# curl：docker compose healthcheck 用
# git：部分 pip 包元数据 / 用户 docker exec 后排查
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        git \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/backend

# ---- 后端 deps（pyproject.toml 不变就缓存这一层）----
# setuptools 的 find_packages 需要在 install 时看到 app/，先用空 stub 占位，
# 后面 COPY backend/ 会用真源码覆盖；editable .egg-link 始终指向 /app/backend
COPY backend/pyproject.toml ./pyproject.toml
RUN mkdir -p app && touch app/__init__.py \
    && pip install --upgrade pip wheel \
    && pip install -e ".[dev]"

# ---- Python 沙盒 venv（requirements.sandbox.txt 不变就缓存这一层）----
# bootstrap_sandbox_venv.sh 从脚本路径上溯一级当 BACKEND_DIR，
# 所以放进 backend/scripts/ 后跑出来的 venv 就在 /app/backend/.venv-sandbox
COPY backend/requirements.sandbox.txt ./requirements.sandbox.txt
COPY backend/scripts/bootstrap_sandbox_venv.sh ./scripts/bootstrap_sandbox_venv.sh
RUN bash ./scripts/bootstrap_sandbox_venv.sh

# ---- 可选 kyuubi CLI（公网 PyPI 可能没有，失败不阻塞 build）----
RUN pip install xiaomi-kyuubi-cli \
    || echo "→ xiaomi-kyuubi-cli 未装（公网 PyPI 不可用）。kyuubi_query 工具会返回 KYUUBI_NOT_CONFIGURED，按需手动安装，详见 docs/SELF_HOSTING.md"

# ---- 后端真实源码（最常变，放最后）----
COPY backend/ /app/backend/

# ---- 顶层 seed 模板（bind mount 会被宿主目录覆盖，但镜像里要有，方便 reset）----
COPY agents /app/agents
COPY skills /app/skills
COPY Makefile /app/Makefile

# ---- 前端 dist（main.py 期望路径：repo_root/frontend/dist）----
COPY --from=frontend-builder /app/dist /app/frontend/dist

EXPOSE 8000

# uvicorn 多 worker：--workers ${ICE_WORKERS:-2} 容器场景小机器友好。
# ws ping/pong 30/60 与 Makefile L13-16、deploy.sh L153 保持一致。
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers ${ICE_WORKERS:-2} --ws-ping-interval 30 --ws-ping-timeout 60"]
