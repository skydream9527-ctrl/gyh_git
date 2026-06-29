# 代码副本说明

源仓库：`https://git.n.xiaomi.com/gongyunhe/ice-workbench`
拷贝时间：2026-05-27
拷贝大小：~8.7M（原始仓库 258M）

## 拷贝时排除的目录与文件

为避免污染当前 git 仓库与泄露密钥，以下内容**未拷贝**：

| 路径 | 原因 |
|---|---|
| `.git/` | 避免嵌套 git 仓库 |
| `.env` | **包含真实 mify API key**，拷贝至此处会随 GitLab 泄露 |
| `backend/.venv/` `backend/.venv-sandbox/` | 124M Python 虚拟环境，可重建 |
| `frontend/node_modules/` | 121M npm 依赖，可重建 |
| `frontend/dist/` | 构建产物，可重建 |
| `.cache/` | 运行时 SQLite 索引，启动时自动重建 |
| `users/{uuid}/` `tasks/{uuid}/` | 运行时用户数据（仅保留 `README.md`） |
| `extracted/` `ice_data_workspace_v2.zip` | 旧版 v2 归档，体积大且不参与构建 |
| `update_file/` `test_file/` | 工作 staging 目录 |
| `__pycache__/` `.pytest_cache/` 等 | 缓存 |

## 用本副本起项目

```bash
cd project/ice-workbench/

# 1. 复制 .env.example 并填好 mify 凭证（向 ice-workbench 维护者要）
cp .env.example .env
# 编辑 .env，至少填 ICE_SECRET_KEY（≥32 字节）和 MIFY_GATEWAY_API_KEY

# 2. 安装依赖
make install

# 3. 启动
make dev          # dev 双端口（:5173 + :8000）
# 或
./deploy.sh --prod # 生产单端口（:8000）
```

详细操作见同级目录 `README.md` 与 [`../../references/ice-workbench-usage-guide.md`](../../references/ice-workbench-usage-guide.md)。
