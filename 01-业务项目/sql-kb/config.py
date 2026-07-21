"""集中配置：模型、路径、检索参数。

要调整行为，改这里即可，不用动其他文件。
"""
from pathlib import Path

# 项目根目录（本文件所在目录）
BASE_DIR = Path(__file__).resolve().parent

# ---- 数据与索引路径 ----
DATA_DIR = BASE_DIR / "data"
JSONL_PATH = BASE_DIR / "requirements.jsonl"   # 解析后的标准记录（一行一条）
CHROMA_DIR = BASE_DIR / "chroma_db"            # Chroma 本地持久化目录
COLLECTION_NAME = "sql_requirements"

# ---- Embedding 模型 ----
# 中文检索强、约 1.3GB，首次运行自动下载到 HuggingFace 本地缓存
EMBED_MODEL = "BAAI/bge-large-zh-v1.5"
# bge-zh 官方建议：检索 query 前加指令前缀可提升效果；被检索的文档侧不加
QUERY_INSTRUCTION = "为这个句子生成表示以用于检索相关文章："

# ---- 检索参数 ----
TOP_K = 5        # 最终返回条数
RECALL_N = 20    # 每路（向量 / BM25）各自召回条数
RRF_K = 60       # RRF 融合常数，越大越平滑（经验值 60）
