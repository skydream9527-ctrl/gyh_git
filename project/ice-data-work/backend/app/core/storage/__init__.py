"""G3 文件优先存储。

文件系统是唯一真相源；SQLite / pgvector 是可重建的派生索引。
对外统一从 app.core.storage 导入，不直接 import 子模块。
"""
from . import paths  # noqa: F401
from .jsonio import read_json, write_json, append_jsonl, read_jsonl  # noqa: F401
from .transaction import file_transaction  # noqa: F401
