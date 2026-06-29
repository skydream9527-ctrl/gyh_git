# Mify 知识库 API 参考

> 来源：https://mify.mioffice.cn/datasets?category=api
> 整理日期：2026-03-09
> API Base URL：`https://service.mify.mioffice.cn/api/v1`

## 鉴权

所有请求需在 `Authorization` Header 中携带 API Key：

```
Authorization: Bearer {API_KEY}
```

---

## 知识库管理

### 知识库列表

```
GET /datasets?page=1&limit=20&provider=vendor
```

Query 参数：`keyword`, `tag_ids`, `page`, `limit`, `provider`（vendor / external / mibrag）

Response:
```json
{
  "data": [
    {
      "id": "",
      "name": "知识库名称",
      "description": "描述信息",
      "permission": "only_me",
      "data_source_type": "upload_file",
      "indexing_technique": "",
      "app_count": 2,
      "document_count": 10,
      "word_count": 1200,
      "created_by": "",
      "created_at": 1695690280,
      "updated_by": "",
      "updated_at": 1695690280,
      "embedding_model": "",
      "embedding_model_provider": "",
      "embedding_available": true
    }
  ]
}
```

### 查看知识库详情

```
GET /datasets/{dataset_id}
```

### 创建知识库

```
POST /datasets
```

Body: `{ name, description, permission ("only_me" | "all_team_members"), provider ("vendor" | "mibrag"), retrieval_model, process_rule }`

### 修改知识库详情

```
PATCH /datasets/{dataset_id}
```

### 删除知识库

```
DELETE /datasets/{dataset_id}
```

Response: `204 No Content`

---

## 文档管理

### 知识库文档列表

```
GET /datasets/{dataset_id}/documents?keyword=&page=1&limit=20
```

Query 参数：`keyword`（搜索文档名称）, `page`, `limit`（默认20，范围1-100）

Response:
```json
{
  "data": [
    {
      "id": "",
      "position": 1,
      "data_source_type": "file_upload",
      "data_source_info": null,
      "dataset_process_rule_id": null,
      "name": "doc_name",
      "created_from": "",
      "created_by": "",
      "created_at": 1681623639,
      "tokens": 0,
      "indexing_status": "waiting",
      "error": null,
      "enabled": true,
      "disabled_at": null,
      "disabled_by": null,
      "archived": false
    }
  ],
  "has_more": false,
  "limit": 20,
  "total": 9,
  "page": 1
}
```

**注意：** 需要分页遍历获取全部文档（`has_more` 为 true 时继续请求）。

### 获取文档详情

```
GET /datasets/{dataset_id}/documents/{document_id}?metadata=all
```

### 通过文件创建文档

```
POST /datasets/{dataset_id}/document/create-by-file
```

Multipart form-data: `file`（二进制）+ `data`（JSON）

### 通过文本创建文档

```
POST /datasets/{dataset_id}/document/create-by-text
```

Body: `{ name, text, indexing_technique, doc_form, process_rule }`

### 通过文件更新文档

```
POST /datasets/{dataset_id}/documents/{document_id}/update-by-file
```

### 通过文本更新文档

```
POST /datasets/{dataset_id}/documents/{document_id}/update-by-text
```

### 删除文档

```
DELETE /datasets/{dataset_id}/documents/{document_id}
```

Response: `204 No Content`

### 获取文档嵌入状态（进度）

```
GET /datasets/{dataset_id}/documents/{batch}/indexing-status
```

Response: `{ "data": [{ "indexing_status": "completed|error|indexing", "error": null }] }`

### 更新文档状态（启用/禁用）

```
POST /datasets/{dataset_id}/documents/{document_id}/status
```

---

## 搜索

### 检索 Mify 知识库（MifyRAG）

```
POST /datasets/{dataset_id}/retrieve
```

Body:
```json
{
  "query": "搜索词",
  "retrieval_model": {
    "search_method": "hybrid_search",
    "reranking_enable": true,
    "top_k": 5,
    "score_threshold": 0.5,
    "score_threshold_enabled": true,
    "reranking_mode": "reranking_model",
    "reranking_model": { "reranking_provider_name": "", "reranking_model_name": "" }
  }
}
```

### 检索 Mi-BRAG 知识库

```
POST /datasets/{dataset_id}/mibrag_retrieve
```

Body:
```json
{
  "query": "搜索词",
  "external_retrieval_model": {
    "top_k": 5,
    "score_threshold": 0.5,
    "score_threshold_enabled": true
  }
}
```

---

## 飞书集成

### 抓取飞书文档目录

```
POST /datasets/feishu/crawl
Header: X-MI-EMAIL: {email}
Body: { "urls": ["https://...feishu.cn/wiki/..."] }
```

### 通过飞书链接创建文档

```
POST /datasets/{dataset_id}/documents/create-by-feishu-url
Header: X-MI-EMAIL: {email}
Body: { indexing_technique, doc_form, frequency, process_rule, docs: [{doc_type, doc_token, title, ...}] }
```

### 同步飞书文档

```
POST /datasets/{dataset_id}/documents/feishu/sync
Header: X-MI-EMAIL: {email}
Body: { "document_ids": ["doc-id-1", ...] }
```

### 更新飞书同步频率

```
POST /datasets/{dataset_id}/documents/update-frequency
Header: X-MI-EMAIL: {email}
Body: { "documents": [{ "document_id": "...", "frequency": 3 }] }
```

---

## 网站爬取

### 创建爬取任务

```
POST /datasets/crawl/website
```

### 获取爬取任务状态

```
GET /datasets/crawl/website/{task_id}
```

### 根据爬取任务创建文档

```
POST /datasets/{dataset_id}/documents/create-by-website
```

---

## 重要发现（与现有代码的差异）

1. **文档列表 API 存在**：`GET /datasets/{dataset_id}/documents` — 现有代码中**未使用**，可用于状态同步
2. **删除文档 API 存在**：`DELETE /datasets/{dataset_id}/documents/{document_id}` — 现有代码中**未实现**
3. **删除知识库 API 存在**：`DELETE /datasets/{dataset_id}` — 现有代码中**未实现**
4. 文档列表支持分页（`has_more` + `page`），遍历时需处理分页
