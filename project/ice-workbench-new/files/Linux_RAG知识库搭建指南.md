# Linux 系统 RAG 知识库配置与搭建指南

> 适用场景：在一台 Linux 服务器上搭建可用于企业文档问答、知识库检索、Agent 增强上下文的 RAG（Retrieval-Augmented Generation）知识库。  
> 推荐路线：`Docker Compose + PostgreSQL/pgvector + FastAPI RAG 服务 + OpenAI-Compatible LLM/Embedding 网关`。  
> 目标读者：需要从 0 到 1 搭建 RAG 知识库的研发、数据、平台或运维同学。

---

## 1. RAG 知识库整体架构

### 1.1 核心链路

```text
文档上传
  -> 文档解析
  -> 文本清洗
  -> Chunk 切分
  -> Embedding 向量化
  -> 向量库 / 元数据入库
  -> 用户提问
  -> 问题向量化
  -> 相似 Chunk 检索
  -> 可选重排 Rerank
  -> 拼接上下文
  -> LLM 生成答案
  -> 返回答案 + 引用来源
```

### 1.2 推荐组件

| 层级 | 推荐组件 | 说明 |
|---|---|---|
| 操作系统 | Ubuntu 22.04 / Debian 12 / Rocky Linux 9 | 服务器部署常见选择 |
| 容器 | Docker + Docker Compose | 降低环境配置复杂度 |
| 向量存储 | PostgreSQL + pgvector | 适合中小型知识库，便于同时存元数据 |
| RAG API | FastAPI | 轻量、易接入现有系统 |
| 文档解析 | Python loaders：pypdf、python-docx、markdown、beautifulsoup4 | 覆盖 PDF / Word / Markdown / HTML / TXT |
| Embedding | OpenAI-compatible embedding API / 本地 embedding 模型 | 按公司环境选择 |
| LLM | OpenAI-compatible Chat Completions API / 本地大模型 | 与现有网关统一最好 |
| 可选重排 | bge-reranker / Jina reranker / 网关 rerank API | 提升召回质量 |
| Web 管理 | 自建简单管理页 / 接入现有平台 | 上传、删除、重建索引 |

---

## 2. 服务器准备

### 2.1 硬件建议

| 规模 | 文档量 | 推荐配置 |
|---|---:|---|
| 个人 / Demo | < 1 万 chunks | 2C4G，50GB SSD |
| 小团队 | 1–50 万 chunks | 4C8G，100–300GB SSD |
| 部门级 | 50–500 万 chunks | 8C16G+，500GB+ SSD，建议独立数据库 |

如果使用本地 LLM 或本地 embedding 模型，需要额外 GPU 或更高 CPU/内存；如果调用公司统一模型网关，普通 CPU 服务器即可。

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

Ubuntu / Debian：

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker
docker version
```

安装 Docker Compose 插件：

```bash
docker compose version
```

如果 `docker compose` 不存在，可安装：

```bash
sudo apt install -y docker-compose-plugin
```

---

## 3. 目录规划

建议统一放在 `/opt/rag-kb`：

```bash
sudo mkdir -p /opt/rag-kb/{app,data,uploads,logs,backups}
sudo chown -R $USER:$USER /opt/rag-kb
cd /opt/rag-kb
```

目录说明：

```text
/opt/rag-kb/
├── app/                 # RAG API 服务代码
├── data/                # PostgreSQL 数据挂载目录
├── uploads/             # 原始文档上传目录
├── logs/                # 应用日志
├── backups/             # 数据库备份
├── .env                 # 环境变量
└── docker-compose.yml   # 服务编排
```

---

## 4. 环境变量配置

在 `/opt/rag-kb/.env` 写入：

```bash
cat > .env <<'EOF'
# ---- PostgreSQL ----
POSTGRES_DB=ragkb
POSTGRES_USER=rag_user
POSTGRES_PASSWORD=change_me_strong_password
POSTGRES_PORT=5432

# ---- RAG API ----
RAG_API_PORT=8088
RAG_UPLOAD_DIR=/app/uploads
RAG_TOP_K=8
RAG_CHUNK_SIZE=800
RAG_CHUNK_OVERLAP=120

# ---- Embedding ----
# 推荐使用 OpenAI-compatible embedding endpoint
EMBEDDING_BASE_URL=https://your-llm-gateway.example.com/v1
EMBEDDING_API_KEY=replace_with_embedding_key
EMBEDDING_MODEL=text-embedding-3-large
EMBEDDING_DIM=3072

# ---- Chat LLM ----
LLM_BASE_URL=https://your-llm-gateway.example.com/v1
LLM_API_KEY=replace_with_llm_key
LLM_MODEL=gpt-4.1-mini

# ---- Security ----
RAG_ADMIN_TOKEN=replace_with_random_admin_token
EOF
```

> 注意：如果 embedding 模型维度不是 3072，要同步修改 `EMBEDDING_DIM` 和数据库建表中的 `vector(...)` 维度。

---

## 5. Docker Compose 部署 PostgreSQL + pgvector

在 `/opt/rag-kb/docker-compose.yml` 写入：

```yaml
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
```

---

## 6. 初始化 RAG API 服务

### 6.1 创建 Python 项目

```bash
mkdir -p /opt/rag-kb/app
cd /opt/rag-kb/app
```

创建 `requirements.txt`：

```bash
cat > requirements.txt <<'EOF'
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

创建 `Dockerfile`：

```bash
cat > Dockerfile <<'EOF'
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

### 6.2 创建数据库初始化脚本

创建 `/opt/rag-kb/app/db.py`：

```python
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
```

---

## 7. 文档解析与切分

创建 `/opt/rag-kb/app/loaders.py`：

```python
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

    if suffix in {".docx"}:
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
```

---

## 8. Embedding 与 LLM 调用

创建 `/opt/rag-kb/app/llm.py`：

```python
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
        "如果上下文不足，明确说不知道。回答时尽量列出引用来源编号。"
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
```

---

## 9. RAG API 服务

创建 `/opt/rag-kb/app/main.py`：

```python
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
```

---

## 10. 启动服务

回到 `/opt/rag-kb`：

```bash
cd /opt/rag-kb
docker compose up -d --build
docker compose ps
```

查看日志：

```bash
docker compose logs -f rag-api
```

健康检查：

```bash
curl http://127.0.0.1:8088/health
```

预期返回：

```json
{"status":"ok"}
```

---

## 11. 上传文档与问答测试

### 11.1 上传文档

```bash
curl -X POST http://127.0.0.1:8088/documents/upload \
  -H "Authorization: Bearer $RAG_ADMIN_TOKEN" \
  -F "file=@/path/to/your-doc.pdf"
```

如果当前 shell 没有加载 `.env`，先执行：

```bash
set -a
source /opt/rag-kb/.env
set +a
```

### 11.2 发起问答

```bash
curl -X POST http://127.0.0.1:8088/query \
  -H "Content-Type: application/json" \
  -d '{"question":"这份文档主要讲了什么？","top_k":5}'
```

返回示例：

```json
{
  "answer": "根据来源 1 和来源 3，文档主要说明了……",
  "sources": [
    {
      "chunk_id": 12,
      "filename": "your-doc.pdf",
      "score": 0.82,
      "content": "..."
    }
  ]
}
```

---

## 12. 生产配置建议

### 12.1 反向代理

建议用 Nginx 暴露 HTTPS：

```nginx
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
```

生产环境建议配置 TLS：

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d rag.example.com
```

### 12.2 防火墙

如果只通过 Nginx 暴露服务，RAG API 端口可以只绑定本地。当前 Compose 已将 PostgreSQL 绑定到 `127.0.0.1`，API 如需内网访问可保留 `0.0.0.0:8088`。

UFW 示例：

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### 12.3 备份

创建备份脚本 `/opt/rag-kb/backup.sh`：

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

配置每日备份：

```bash
crontab -e
```

加入：

```cron
0 3 * * * /opt/rag-kb/backup.sh >> /opt/rag-kb/logs/backup.log 2>&1
```

---

## 13. 检索质量优化

### 13.1 Chunk 切分优化

默认配置：

```text
RAG_CHUNK_SIZE=800
RAG_CHUNK_OVERLAP=120
```

建议：

| 文档类型 | chunk_size | overlap |
|---|---:|---:|
| FAQ / 短知识 | 300–500 | 50–80 |
| 产品文档 | 600–900 | 100–150 |
| 技术规范 | 800–1200 | 120–200 |
| 法务/制度 | 1000–1500 | 150–250 |

### 13.2 混合检索

仅向量检索可能漏掉精确关键词，例如版本号、错误码、字段名。建议后续增加：

1. PostgreSQL 全文检索 `tsvector`。
2. 向量召回 top 20。
3. 关键词召回 top 20。
4. RRF 合并。
5. Rerank 取 top 5–10。

### 13.3 引用来源

生产环境务必返回：

- 文档名
- chunk id
- 原文片段
- 相似度分数
- 页码 / 标题路径（如果解析器支持）

否则用户无法判断答案是否可信。

---

## 14. 常见问题排查

### 14.1 pgvector 维度不匹配

现象：插入 embedding 时报错维度不一致。

处理：

1. 确认 embedding 模型真实输出维度。
2. 修改 `.env` 的 `EMBEDDING_DIM`。
3. 重新建表或迁移表结构。

开发测试阶段可直接重建：

```bash
docker compose down
rm -rf data/postgres
docker compose up -d --build
```

生产环境不要直接删除数据，应写迁移脚本并重新向量化。

### 14.2 上传 PDF 后内容为空

原因：PDF 是扫描件，没有文本层。

处理：

- 增加 OCR：PaddleOCR / Tesseract。
- 或先将扫描 PDF 转成可复制文本的 PDF。

### 14.3 答案胡编

处理：

1. System prompt 中明确“只能基于上下文回答”。
2. 如果召回为空，直接返回不知道。
3. 降低 temperature。
4. 返回引用来源。
5. 增加 rerank。

### 14.4 召回不准

处理顺序：

1. 调整 chunk 大小和 overlap。
2. 检查文档解析质量。
3. 增加 metadata 过滤，例如业务线、文档类型、更新时间。
4. 增加混合检索。
5. 增加 rerank。

### 14.5 API 访问慢

排查：

```bash
docker compose logs -f rag-api
docker stats
```

常见原因：

- embedding 或 LLM 网关慢。
- top_k 太大。
- 没有向量索引或索引未生效。
- 数据库和 API 在同一小机器上资源不足。

---

## 15. 与现有系统集成建议

### 15.1 作为独立知识库服务

其他系统通过 HTTP 调用：

```text
POST /query
POST /documents/upload
```

适合：快速上线、低耦合。

### 15.2 接入 Agent 工具

可以把 RAG 查询封装成 Agent tool：

```json
{
  "name": "rag_search",
  "description": "Search private knowledge base and return relevant chunks with citations",
  "parameters": {
    "query": "string",
    "top_k": "integer"
  }
}
```

Agent 使用方式：

```text
用户问业务知识 / 指标口径 / 历史方案
  -> 调 rag_search
  -> 基于返回 chunks 回答
  -> 必须带引用来源
```

### 15.3 接入 ICE Workbench

如果接入当前 ICE Workbench 项目，建议：

1. 在后端新增 `rag_search` 工具。
2. 在 `skills/` 中新增 RAG 使用说明 skill。
3. 给需要知识库能力的 Agent 添加工具白名单。
4. 将 RAG 服务 URL/API Key 放到 `.env`。
5. 在工具返回中包含 `sources`，方便 Agent 引用。

---

## 16. 最小上线 Checklist

- [ ] Linux 服务器基础依赖安装完成。
- [ ] Docker / Docker Compose 可用。
- [ ] `/opt/rag-kb/.env` 已配置强密码和模型网关。
- [ ] PostgreSQL + pgvector 启动成功。
- [ ] `/health` 返回 `ok`。
- [ ] 上传 PDF / Markdown / DOCX 测试成功。
- [ ] `/query` 能返回答案和引用来源。
- [ ] Nginx HTTPS 配置完成。
- [ ] 管理 token 已设置且没有泄露。
- [ ] 数据库和上传目录已配置每日备份。
- [ ] 生产文档上传前明确权限和脱敏策略。

---

## 17. 后续增强路线

| 阶段 | 能力 | 说明 |
|---|---|---|
| P0 | 基础上传 + 检索问答 | 当前文档覆盖 |
| P1 | 文档删除 / 重建索引 / 增量更新 | 支持知识库维护 |
| P1 | metadata filter | 按业务线、文档类型、权限过滤 |
| P1 | 混合检索 | 向量 + 关键词 |
| P1 | rerank | 提升上下文质量 |
| P2 | 权限系统 | 不同用户访问不同知识范围 |
| P2 | OCR | 支持扫描 PDF / 图片 |
| P2 | 前端管理台 | 上传、搜索、删除、查看 chunks |
| P3 | 多知识库空间 | 团队级 / 项目级 / 个人级知识库 |

---

## 18. 推荐默认方案

如果只是要快速在 Linux 上搭建一个可用的 RAG 知识库，建议采用：

```text
Ubuntu 22.04
Docker Compose
PostgreSQL 16 + pgvector
FastAPI RAG API
公司统一 OpenAI-compatible LLM 网关
Nginx + HTTPS
每日 pg_dump + uploads 备份
```

这套方案部署简单、可维护性好，也方便后续接入 ICE Workbench 或其他 Agent 平台。
