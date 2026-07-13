# 给 TRAE 的 RAG 知识库安装部署操作清单

> 用途：这是一份可以直接交给 TRAE / AI 编程助手 / 运维同学执行的 RAG 知识库安装部署清单。  
> 目标：在 Linux 服务器上部署一个可用的 RAG 知识库服务，并预留接入 ICE Workbench Agent 的配置。  
> 推荐技术栈：Docker Compose + PostgreSQL/pgvector + FastAPI RAG API + OpenAI-Compatible Embedding/LLM 网关。  
> 相关参考文档：`files/Linux_RAG知识库搭建指南.md`、`files/RAG知识库接入项目Agent调用指南.md`。

---

## 0. 给 TRAE 的任务说明

请你在目标 Linux 服务器上完成 RAG 知识库的安装、配置、启动、验证和交付。要求：

1. 使用 Docker Compose 部署 PostgreSQL + pgvector 和 RAG API。
2. RAG API 支持文档上传、文档切分、Embedding 入库、问题检索、LLM 回答、返回引用来源。
3. 所有服务配置统一放在 `/opt/rag-kb/.env`。
4. 服务启动后必须完成健康检查、上传测试文档、问答测试。
5. 输出最终交付信息：服务地址、目录结构、启动/停止命令、测试命令、备份方式、待用户补充的密钥项。
6. 不要把任何 API Key、Token、密码写入代码仓库或文档正文，只写入服务器 `.env`。

---

## 1. 部署前确认清单

### 1.1 需要用户提前提供

| 项目 | 示例 | 是否必填 |
|---|---|---|
| Linux 服务器登录方式 | SSH 用户名 / IP / 密钥 | 必填 |
| RAG 服务端口 | `8088` | 必填，可默认 |
| PostgreSQL 密码 | 强随机密码 | 必填 |
| RAG 管理 Token | 强随机 token | 必填 |
| Embedding API Base URL | `https://xxx/v1` | 必填 |
| Embedding API Key | `<embedding-api-key>`（保密，运行时注入，勿入库） | 必填 |
| Embedding 模型名 | `text-embedding-3-large` | 必填 |
| Embedding 维度 | `3072` / `1024` / `768` | 必填 |
| LLM API Base URL | `https://xxx/v1` | 必填 |
| LLM API Key | `<llm-api-key>`（保密，运行时注入，勿入库） | 必填 |
| LLM 模型名 | `gpt-4.1-mini` / 公司网关模型 | 必填 |
| 域名 | `rag.example.com` | 可选 |
| 是否配置 HTTPS | 是 / 否 | 可选 |

### 1.2 服务器最低要求

```text
CPU: 2 核以上
内存: 4GB 以上
磁盘: 50GB 以上 SSD
系统: Ubuntu 22.04 / Debian 12 / Rocky Linux 9
网络: 能访问 Embedding 与 LLM API 网关
```

### 1.3 风险提醒

- 如果 embedding 模型维度填错，向量入库会失败。
- 如果 PDF 是扫描件，默认解析可能为空，需要后续加 OCR。
- 如果 RAG 服务部署在公网，必须配置鉴权、HTTPS 和防火墙。
- 如果知识库包含敏感文档，必须在 RAG 服务侧做权限过滤，不能只依赖 Agent prompt。

---

## 2. 服务器基础环境安装

### 2.1 登录服务器

```bash
ssh <user>@<server_ip>
```

### 2.2 安装基础依赖

Ubuntu / Debian：

```bash
sudo apt update
sudo apt install -y ca-certificates curl gnupg git unzip jq python3 python3-venv python3-pip
```

Rocky Linux / CentOS Stream：

```bash
sudo dnf install -y ca-certificates curl git unzip jq python3 python3-pip
```

### 2.3 安装 Docker

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker
docker version
docker compose version
```

如果 `docker compose version` 不可用，Ubuntu / Debian 执行：

```bash
sudo apt install -y docker-compose-plugin
docker compose version
```

验收标准：

```text
docker version 能正常输出 Client / Server 信息。
docker compose version 能正常输出版本号。
```

---

## 3. 创建部署目录

```bash
sudo mkdir -p /opt/rag-kb/{app,data,uploads,logs,backups}
sudo chown -R $USER:$USER /opt/rag-kb
cd /opt/rag-kb
```

验收：

```bash
find /opt/rag-kb -maxdepth 2 -type d | sort
```

预期至少包含：

```text
/opt/rag-kb
/opt/rag-kb/app
/opt/rag-kb/backups
/opt/rag-kb/data
/opt/rag-kb/logs
/opt/rag-kb/uploads
```

---

## 4. 创建 `.env`

`.env` 只允许存在于服务器本地，权限 `600`，且已被 `.gitignore` 排除，严禁提交到代码仓库。真实密钥不写入本文档，只在服务器 shell 会话中临时注入。

第 1 步：把用户 / 密钥管理系统提供的敏感信息注入当前 shell（等号右边替换为真实值。为避免落入命令历史，可在命令前加一个空格，或先 `unset HISTFILE`）：

```bash
export EMBEDDING_BASE_URL='填入真实 Embedding 网关地址，例如 https://gateway.internal/v1'
export EMBEDDING_API_KEY='填入真实 Embedding API Key'
export LLM_BASE_URL='填入真实 LLM 网关地址，例如 https://gateway.internal/v1'
export LLM_API_KEY='填入真实 LLM API Key'
```

第 2 步：自动生成高强度的数据库密码与管理 Token，避免弱口令，也避免任何明文写进文档：

```bash
export POSTGRES_PASSWORD="$(openssl rand -hex 24)"
export RAG_ADMIN_TOKEN="$(openssl rand -hex 32)"
```

第 3 步：生成服务器本地 `.env`。文件内容只引用上面的环境变量，正文不出现任何明文密钥：

```bash
cat > /opt/rag-kb/.env <<EOF
# ---- PostgreSQL ----
POSTGRES_DB=ragkb
POSTGRES_USER=rag_user
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
POSTGRES_PORT=5432

# ---- RAG API ----
RAG_API_PORT=8088
RAG_UPLOAD_DIR=/app/uploads
RAG_TOP_K=8
RAG_CHUNK_SIZE=800
RAG_CHUNK_OVERLAP=120

# ---- Embedding ----
EMBEDDING_BASE_URL=${EMBEDDING_BASE_URL}
EMBEDDING_API_KEY=${EMBEDDING_API_KEY}
EMBEDDING_MODEL=text-embedding-3-large
EMBEDDING_DIM=3072

# ---- Chat LLM ----
LLM_BASE_URL=${LLM_BASE_URL}
LLM_API_KEY=${LLM_API_KEY}
LLM_MODEL=gpt-4.1-mini

# ---- Security ----
RAG_ADMIN_TOKEN=${RAG_ADMIN_TOKEN}
EOF

chmod 600 /opt/rag-kb/.env
```

验收：

```bash
cd /opt/rag-kb
set -a
source .env
set +a
test -n "$POSTGRES_PASSWORD" && test -n "$EMBEDDING_API_KEY" && test -n "$LLM_API_KEY" && echo "env ok"
```

预期输出：

```text
env ok
```

---

## 5. 创建 Docker Compose 文件

在 `/opt/rag-kb/docker-compose.yml` 写入：

```bash
cat > /opt/rag-kb/docker-compose.yml <<'EOF'
services:
  postgres:
    image: pgvector/pgvector:pg16
    container_name: rag-postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    ports:
      - "127.0.0.1:${POSTGRES_PORT}:5432"
    volumes:
      - ./data/postgres:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 10

  rag-api:
    build: ./app
    container_name: rag-api
    restart: unless-stopped
    depends_on:
      postgres:
        condition: service_healthy
    env_file:
      - .env
    environment:
      DATABASE_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
    ports:
      - "0.0.0.0:${RAG_API_PORT}:8088"
    volumes:
      - ./uploads:/app/uploads
      - ./logs:/app/logs
EOF
```

验收：

```bash
docker compose config >/tmp/rag-compose-check.yml && echo "compose ok"
```

---

## 6. 创建 RAG API 应用代码

### 6.1 创建 `requirements.txt`

```bash
cat > /opt/rag-kb/app/requirements.txt <<'EOF'
fastapi==0.115.6
uvicorn[standard]==0.34.0
psycopg[binary]==3.2.3
pgvector==0.3.6
pydantic==2.10.4
pydantic-settings==2.7.0
python-multipart==0.0.20
httpx==0.28.1
pypdf==5.1.0
python-docx==1.1.2
beautifulsoup4==4.12.3
markdown==3.7
tiktoken==0.8.0
EOF
```

### 6.2 创建 `Dockerfile`

```bash
cat > /opt/rag-kb/app/Dockerfile <<'EOF'
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app
EXPOSE 8088

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8088"]
EOF
```

### 6.3 创建 `db.py`

```bash
cat > /opt/rag-kb/app/db.py <<'EOF'
import os
import psycopg
from pgvector.psycopg import register_vector


DATABASE_URL = os.getenv("DATABASE_URL")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "3072"))


def get_conn():
    conn = psycopg.connect(DATABASE_URL)
    register_vector(conn)
    return conn


def init_db():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS documents (
                    id BIGSERIAL PRIMARY KEY,
                    filename TEXT NOT NULL,
                    source_path TEXT,
                    content_type TEXT,
                    created_at TIMESTAMPTZ DEFAULT now()
                );

                CREATE TABLE IF NOT EXISTS chunks (
                    id BIGSERIAL PRIMARY KEY,
                    document_id BIGINT REFERENCES documents(id) ON DELETE CASCADE,
                    chunk_index INT NOT NULL,
                    content TEXT NOT NULL,
                    metadata JSONB DEFAULT '{{}}'::jsonb,
                    embedding vector({EMBEDDING_DIM}),
                    created_at TIMESTAMPTZ DEFAULT now()
                );

                CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id);
                CREATE INDEX IF NOT EXISTS idx_chunks_embedding
                ON chunks USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100);
                """
            )
            conn.commit()
EOF
```

### 6.4 创建 `loaders.py`

```bash
cat > /opt/rag-kb/app/loaders.py <<'EOF'
from pathlib import Path

from bs4 import BeautifulSoup
from docx import Document
from pypdf import PdfReader


def load_text(path: str) -> str:
    p = Path(path)
    suffix = p.suffix.lower()

    if suffix in {".txt", ".md", ".csv", ".json", ".sql", ".py"}:
        return p.read_text(encoding="utf-8", errors="ignore")

    if suffix == ".pdf":
        reader = PdfReader(str(p))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    if suffix == ".docx":
        doc = Document(str(p))
        return "\n".join(paragraph.text for paragraph in doc.paragraphs)

    if suffix in {".html", ".htm"}:
        soup = BeautifulSoup(p.read_text(encoding="utf-8", errors="ignore"), "html.parser")
        return soup.get_text("\n")

    raise ValueError(f"unsupported file type: {suffix}")


def split_text(text: str, chunk_size: int = 800, overlap: int = 120) -> list[str]:
    text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    if not text:
        return []

    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == len(text):
            break
        start = max(0, end - overlap)
    return chunks
EOF
```

### 6.5 创建 `llm.py`

```bash
cat > /opt/rag-kb/app/llm.py <<'EOF'
import os
import httpx


EMBEDDING_BASE_URL = os.getenv("EMBEDDING_BASE_URL", "").rstrip("/")
EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", "")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "").rstrip("/")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4.1-mini")


async def embed_texts(texts: list[str]) -> list[list[float]]:
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{EMBEDDING_BASE_URL}/embeddings",
            headers={"Authorization": f"Bearer {EMBEDDING_API_KEY}"},
            json={"model": EMBEDDING_MODEL, "input": texts},
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        return [item["embedding"] for item in data]


async def chat_answer(question: str, contexts: list[dict]) -> str:
    context_text = "\n\n".join(
        f"[来源 {idx + 1}] {item['content']}"
        for idx, item in enumerate(contexts)
    )
    system = (
        "你是一个企业知识库问答助手。只能基于给定上下文回答。"
        "如果上下文不足，明确说不知道。回答时列出引用来源编号。"
    )
    user = f"""请基于以下知识库片段回答问题。

## 知识库片段
{context_text}

## 问题
{question}
"""

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{LLM_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {LLM_API_KEY}"},
            json={
                "model": LLM_MODEL,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0.2,
            },
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
EOF
```

### 6.6 创建 `main.py`

```bash
cat > /opt/rag-kb/app/main.py <<'EOF'
import os
import shutil
from pathlib import Path

from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from pydantic import BaseModel

from db import get_conn, init_db
from llm import chat_answer, embed_texts
from loaders import load_text, split_text


ADMIN_TOKEN = os.getenv("RAG_ADMIN_TOKEN", "")
UPLOAD_DIR = Path(os.getenv("RAG_UPLOAD_DIR", "/app/uploads"))
CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "120"))
TOP_K = int(os.getenv("RAG_TOP_K", "8"))


app = FastAPI(title="RAG Knowledge Base")


class QueryRequest(BaseModel):
    question: str
    top_k: int | None = None


def require_admin(authorization: str | None):
    if not ADMIN_TOKEN:
        raise HTTPException(status_code=500, detail="RAG_ADMIN_TOKEN not configured")
    expected = f"Bearer {ADMIN_TOKEN}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="unauthorized")


@app.on_event("startup")
def startup():
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    authorization: str | None = Header(default=None),
):
    require_admin(authorization)

    target = UPLOAD_DIR / file.filename
    with target.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    text = load_text(str(target))
    chunks = split_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)
    if not chunks:
        raise HTTPException(status_code=400, detail="empty document")

    embeddings = await embed_texts(chunks)

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO documents (filename, source_path, content_type) VALUES (%s, %s, %s) RETURNING id",
                (file.filename, str(target), file.content_type),
            )
            document_id = cur.fetchone()[0]
            for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                cur.execute(
                    """
                    INSERT INTO chunks (document_id, chunk_index, content, metadata, embedding)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (document_id, idx, chunk, {"filename": file.filename}, embedding),
                )
            conn.commit()

    return {"document_id": document_id, "filename": file.filename, "chunks": len(chunks)}


@app.post("/query")
async def query(req: QueryRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="question is required")

    query_embedding = (await embed_texts([req.question]))[0]
    top_k = req.top_k or TOP_K

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT c.id, c.content, c.metadata, d.filename,
                       1 - (c.embedding <=> %s) AS score
                FROM chunks c
                JOIN documents d ON d.id = c.document_id
                ORDER BY c.embedding <=> %s
                LIMIT %s
                """,
                (query_embedding, query_embedding, top_k),
            )
            rows = cur.fetchall()

    contexts = [
        {
            "chunk_id": row[0],
            "content": row[1],
            "metadata": row[2],
            "filename": row[3],
            "score": float(row[4]),
        }
        for row in rows
    ]
    answer = await chat_answer(req.question, contexts)
    return {"answer": answer, "sources": contexts}
EOF
```

验收：

```bash
find /opt/rag-kb/app -maxdepth 1 -type f | sort
```

预期包含：

```text
Dockerfile
db.py
llm.py
loaders.py
main.py
requirements.txt
```

---

## 7. 启动服务

```bash
cd /opt/rag-kb
docker compose up -d --build
docker compose ps
```

验收标准：

```text
rag-postgres 状态为 healthy 或 running
rag-api 状态为 running
```

查看日志：

```bash
docker compose logs --tail=100 rag-api
docker compose logs --tail=100 postgres
```

---

## 8. 健康检查

```bash
curl -s http://127.0.0.1:8088/health | jq
```

预期：

```json
{
  "status": "ok"
}
```

如果失败，执行：

```bash
docker compose ps
docker compose logs -f rag-api
```

---

## 9. 上传测试文档

### 9.1 创建测试文档

```bash
cat > /tmp/rag_test_doc.md <<'EOF'
# RAG 测试文档

ICE Workbench 的 RAG 知识库用于帮助 Agent 查询企业文档、指标口径、SOP 和历史分析报告。

当用户询问知识库相关问题时，Agent 应先检索 RAG，再基于引用来源回答。

如果知识库没有命中，Agent 不应该编造答案，而应该说明未检索到相关内容。
EOF
```

### 9.2 上传文档

```bash
cd /opt/rag-kb
set -a
source .env
set +a

curl -s -X POST http://127.0.0.1:8088/documents/upload \
  -H "Authorization: Bearer $RAG_ADMIN_TOKEN" \
  -F "file=@/tmp/rag_test_doc.md" | jq
```

预期包含：

```json
{
  "document_id": 1,
  "filename": "rag_test_doc.md",
  "chunks": 1
}
```

如果这里失败，优先检查：

```bash
docker compose logs --tail=200 rag-api
```

常见问题：

| 现象 | 可能原因 |
|---|---|
| `401 unauthorized` | `RAG_ADMIN_TOKEN` 不匹配 |
| Embedding 接口 401 | `EMBEDDING_API_KEY` 错误 |
| Embedding 维度报错 | `EMBEDDING_DIM` 与模型输出不一致 |
| timeout | 服务器无法访问模型网关 |

---

## 10. 查询测试

```bash
curl -s -X POST http://127.0.0.1:8088/query \
  -H "Content-Type: application/json" \
  -d '{"question":"Agent 查询知识库时应该怎么做？","top_k":5}' | jq
```

验收标准：

```text
返回 JSON 中包含 answer。
返回 JSON 中包含 sources。
sources 至少 1 条。
sources[0].filename 为 rag_test_doc.md。
answer 语义上能回答“先检索 RAG，再基于引用来源回答”。
```

---

## 11. 数据库验证

```bash
cd /opt/rag-kb
set -a
source .env
set +a

docker exec -it rag-postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT count(*) AS documents FROM documents;"
docker exec -it rag-postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT count(*) AS chunks FROM chunks;"
```

预期：

```text
documents >= 1
chunks >= 1
```

---

## 12. 配置防火墙

如果需要外部访问 RAG API：

```bash
sudo ufw allow OpenSSH
sudo ufw allow 8088/tcp
sudo ufw enable
sudo ufw status
```

如果后续使用 Nginx + HTTPS，只开放 80/443，不建议直接开放 8088：

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

---

## 13. 可选：配置 Nginx 反向代理

如果用户提供域名 `rag.example.com`，安装 Nginx：

```bash
sudo apt install -y nginx
```

创建配置：

```bash
sudo tee /etc/nginx/sites-available/rag-kb >/dev/null <<'EOF'
server {
    listen 80;
    server_name rag.example.com;

    location / {
        proxy_pass http://127.0.0.1:8088;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/rag-kb /etc/nginx/sites-enabled/rag-kb
sudo nginx -t
sudo systemctl reload nginx
```

验证：

```bash
curl -s http://rag.example.com/health | jq
```

---

## 14. 可选：配置 HTTPS

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d rag.example.com
```

验证：

```bash
curl -s https://rag.example.com/health | jq
```

---

## 15. 配置备份

创建 `/opt/rag-kb/backup.sh`：

```bash
cat > /opt/rag-kb/backup.sh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

cd /opt/rag-kb
set -a
source .env
set +a

ts=$(date +%Y%m%d_%H%M%S)
mkdir -p backups

docker exec rag-postgres pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > "backups/ragkb_${ts}.sql"
tar -czf "backups/uploads_${ts}.tar.gz" uploads

find backups -type f -mtime +14 -delete
echo "backup done: $ts"
EOF

chmod +x /opt/rag-kb/backup.sh
```

手动执行一次：

```bash
/opt/rag-kb/backup.sh
ls -lh /opt/rag-kb/backups | tail
```

加入 crontab：

```bash
(crontab -l 2>/dev/null; echo "0 3 * * * /opt/rag-kb/backup.sh >> /opt/rag-kb/logs/backup.log 2>&1") | crontab -
crontab -l
```

---

## 16. 启停与运维命令

### 16.1 启动

```bash
cd /opt/rag-kb
docker compose up -d
```

### 16.2 停止

```bash
cd /opt/rag-kb
docker compose down
```

### 16.3 重启 API

```bash
cd /opt/rag-kb
docker compose restart rag-api
```

### 16.4 查看状态

```bash
cd /opt/rag-kb
docker compose ps
docker stats --no-stream
```

### 16.5 查看日志

```bash
cd /opt/rag-kb
docker compose logs -f rag-api
```

### 16.6 更新服务代码后重新构建

```bash
cd /opt/rag-kb
docker compose up -d --build
```

---

## 17. 接入 ICE Workbench Agent 的预留配置

如果 RAG 服务要给当前 ICE Workbench Agent 调用，在 ICE Workbench 项目的 `.env` 中增加：

```bash
RAG_KB_ENABLED=true
RAG_KB_BASE_URL=http://127.0.0.1:8088
# 值需与服务器 /opt/rag-kb/.env 中的 RAG_ADMIN_TOKEN 一致；由密钥管理系统注入，切勿硬编码
RAG_KB_API_KEY=
RAG_KB_TIMEOUT_SEC=30
RAG_KB_DEFAULT_TOP_K=5
```

如果 ICE Workbench 在 Docker 容器中，且 RAG 服务在宿主机：

```bash
RAG_KB_BASE_URL=http://host.docker.internal:8088
```

Linux Docker 需要在 ICE Workbench compose 中加：

```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

如果 RAG 服务和 ICE Workbench 同一个 Docker Compose 网络：

```bash
RAG_KB_BASE_URL=http://rag-api:8088
```

---

## 18. TRAE 交付物清单

完成部署后，请给用户输出以下信息：

```markdown
## RAG 知识库部署交付

### 服务信息
- 部署目录：/opt/rag-kb
- RAG API 本机地址：http://127.0.0.1:8088
- RAG API 内网/公网地址：<如果有>
- 健康检查：GET /health

### 已部署容器
- rag-postgres：PostgreSQL + pgvector
- rag-api：FastAPI RAG 服务

### 核心命令
- 启动：cd /opt/rag-kb && docker compose up -d
- 停止：cd /opt/rag-kb && docker compose down
- 重启 API：cd /opt/rag-kb && docker compose restart rag-api
- 查看日志：cd /opt/rag-kb && docker compose logs -f rag-api
- 备份：/opt/rag-kb/backup.sh

### 验证结果
- /health：通过 / 未通过
- 上传测试文档：通过 / 未通过
- 查询测试：通过 / 未通过
- 数据库 documents/chunks 数量：documents=N, chunks=N

### 重要配置
- .env 路径：/opt/rag-kb/.env
- 上传目录：/opt/rag-kb/uploads
- 备份目录：/opt/rag-kb/backups

### 待用户确认
- 是否绑定域名和 HTTPS
- 是否接入 ICE Workbench Agent
- 是否增加权限过滤
- 是否增加 OCR
```

---

## 19. 最终验收 Checklist

请逐项确认：

- [ ] Docker 和 Docker Compose 安装成功。
- [ ] `/opt/rag-kb` 目录创建完成。
- [ ] `.env` 已配置真实 PostgreSQL 密码、RAG token、Embedding/LLM 网关。
- [ ] `docker compose config` 校验通过。
- [ ] `docker compose up -d --build` 启动成功。
- [ ] `rag-postgres` 容器正常。
- [ ] `rag-api` 容器正常。
- [ ] `GET /health` 返回 `{"status":"ok"}`。
- [ ] 测试文档上传成功。
- [ ] 问答查询返回 `answer` 和 `sources`。
- [ ] 数据库中 `documents >= 1`。
- [ ] 数据库中 `chunks >= 1`。
- [ ] 备份脚本可手动执行成功。
- [ ] crontab 已配置每日备份。
- [ ] 如果开放公网，防火墙和 HTTPS 已处理。
- [ ] 已输出交付物清单给用户。

---

## 20. 常见失败处理

### 20.1 Docker 构建失败

执行：

```bash
cd /opt/rag-kb
docker compose build --no-cache rag-api
```

查看错误是否为网络无法下载 pip 包。如果是网络问题，需要配置 pip 镜像或代理。

### 20.2 API 启动失败

执行：

```bash
docker compose logs --tail=200 rag-api
```

重点检查：

- `DATABASE_URL` 是否正确。
- PostgreSQL 是否 healthy。
- `EMBEDDING_DIM` 是否为整数。
- Python import 是否失败。

### 20.3 上传文档失败

执行：

```bash
docker compose logs --tail=200 rag-api
```

重点检查：

- `RAG_ADMIN_TOKEN` 是否正确。
- Embedding 网关是否可访问。
- Embedding API Key 是否有效。
- 文档是否为空或格式不支持。

### 20.4 查询没有来源

检查数据库：

```bash
docker exec -it rag-postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT id, filename FROM documents ORDER BY id DESC LIMIT 5;"
docker exec -it rag-postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT id, document_id, left(content, 80) FROM chunks ORDER BY id DESC LIMIT 5;"
```

如果 chunks 为空，说明上传阶段没有成功入库。

### 20.5 答案质量差

优先调整：

```bash
RAG_CHUNK_SIZE=600
RAG_CHUNK_OVERLAP=100
RAG_TOP_K=10
```

然后重建索引。生产环境需要做文档重切分和重新 embedding。

---

## 21. 给 TRAE 的执行原则

1. 先完成最小闭环：启动、上传、查询、返回 sources。
2. 不要一开始就做复杂前端、权限系统、OCR、rerank。
3. 遇到模型网关错误，先打印 HTTP 状态码和响应摘要，不要泄露 API Key。
4. 所有密钥只写 `.env`，不要写入 Git 仓库。
5. 每完成一个阶段就执行对应验收命令。
6. 最终必须给用户输出“部署交付物清单”。
