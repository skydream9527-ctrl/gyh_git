"""需求记录的数据结构与校验。

一条记录 = 一个「取数子需求」（一段注释描述 + 对应 SQL）。
向量只嵌 source + title + desc，不嵌 SQL（SQL 关键词会污染语义）。
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

# 字段说明（供 README / 校验参考）
FIELDS = {
    "id": "唯一标识，如 req-042",
    "title": "子需求标题（取自该段的首行注释）",
    "desc": "需求描述（该段的注释合并；检索主要匹配这里）",
    "sql": "对应的 SQL",
    "tables": "涉及的来源表（从 SQL 自动抽取，已排除 CTE 别名）",
    "biz_line": "业务线（来自文件级 @业务线 标注，可选）",
    "date": "日期 YYYY-MM-DD（从文件名 yymmdd 解析）",
    "author": "需求方（来自文件级 @需求方 标注，可选）",
    "source": "来源文件 / 需求组名（同一文件的多段共享）",
}


@dataclass
class Requirement:
    id: str
    title: str
    desc: str = ""
    sql: str = ""
    tables: list[str] = field(default_factory=list)
    biz_line: str = ""
    date: str = ""
    author: str = ""
    source: str = ""

    def to_embedding_text(self) -> str:
        """向量化文本：需求组 + 标题 + 描述，不含 SQL。"""
        parts = [self.source.strip(), self.title.strip(), self.desc.strip()]
        return "\n".join(p for p in parts if p)

    def bm25_text(self) -> str:
        """关键词检索文本：标题 + 描述 + 表名 + 需求组（让表名/主题能被精确命中）。"""
        return "\n".join([self.title, self.desc, " ".join(self.tables), self.source])

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_chroma_metadata(self) -> dict[str, Any]:
        """Chroma metadata 只接受 str/int/float/bool，list 转成逗号串。"""
        return {
            "title": self.title,
            "tables": ",".join(self.tables),
            "biz_line": self.biz_line,
            "date": self.date,
            "author": self.author,
            "source": self.source,
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Requirement":
        return Requirement(
            id=str(d.get("id", "")).strip(),
            title=str(d.get("title", "")).strip(),
            desc=str(d.get("desc", "")).strip(),
            sql=str(d.get("sql", "")).strip(),
            tables=list(d.get("tables", []) or []),
            biz_line=str(d.get("biz_line", "")).strip(),
            date=str(d.get("date", "")).strip(),
            author=str(d.get("author", "")).strip(),
            source=str(d.get("source", "")).strip(),
        )

    def validate(self) -> list[str]:
        """返回问题列表；空列表表示通过。"""
        problems = []
        if not self.id:
            problems.append("缺少 id")
        if not self.title and not self.desc:
            problems.append("title 与 desc 至少要有一个（检索靠它们）")
        if not self.sql:
            problems.append("缺少 sql")
        return problems
