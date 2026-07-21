"""把「取数脚本」文档解析成标准 jsonl（一行一条子需求）。

★ 这是唯一依赖你真实文档格式的模块。★
适配的真实格式（见 data/真实样例/）：
  - 一个文件 = 一个分析任务；文件名形如 `260706PUSH链路分析`（yymmdd + 需求名）
  - 文件内多条 SQL（以 `;` 结束）；每条 SQL 上方的 `----` 注释 = 它的描述
  - 没有独立描述注释的 SQL（如 count 校验、导出）自动并入上一条记录
  - 文件级元信息用注释标注：`---- @业务线: 增长` / `---- @需求方: 张三`
  - tables 从 SQL 自动抽取，并排除 CTE 别名（with xxx as (...)）

切分规则：按 `;` 分句 + 段间 `----` 注释归属。CTE 内部的注释在语句内部，不会误触发分段。

用法：
  python parse.py                          # 默认解析 data/真实样例/
  python parse.py data/真实样例             # 指定目录（遍历其中所有文件）
  python parse.py data/某文件 -o out.jsonl  # 指定单个文件
"""
from __future__ import annotations

import re
from pathlib import Path

import config
from schema import Requirement

# 从 SQL 抽 FROM / JOIN 后的表名（支持 库.schema.表 三段命名）
TABLE_RE = re.compile(r'\b(?:from|join)\s+([`"\[]?[\w.]+[`"\]]?)', re.IGNORECASE)
# CTE 定义：xxx as (
CTE_RE = re.compile(r"\b([A-Za-z_]\w*)\s+as\s*\(", re.IGNORECASE)
# 文件级元信息：@业务线: xxx （注释前缀已去除）
META_RE = re.compile(r"^@\s*([A-Za-z_\u4e00-\u9fff]+)\s*[:：]\s*(.+)$")

# 元信息键归一化（兼容中英写法）
KEY_MAP = {
    "业务线": "业务线", "业务": "业务线", "biz": "业务线", "biz_line": "业务线",
    "需求方": "需求方", "需求人": "需求方", "提出人": "需求方", "author": "需求方",
}


def clean_comment(line: str) -> str:
    """去掉行首的注释符 ---- / -- 与空白。"""
    return re.sub(r"^-+\s*", "", line.strip()).strip()


def extract_ctes(sql: str) -> set[str]:
    return {m.group(1).lower() for m in CTE_RE.finditer(sql or "")}


def extract_tables(sql: str) -> list[str]:
    """抽取来源表，去重保序，排除 CTE 别名与子查询。"""
    ctes = extract_ctes(sql)
    out: list[str] = []
    seen: set[str] = set()
    for m in TABLE_RE.finditer(sql or ""):
        t = m.group(1).strip('`"[]')
        low = t.lower()
        if not t or t.startswith("(") or low in ctes or low in seen:
            continue
        seen.add(low)
        out.append(t)
    return out


def parse_filename(name: str) -> tuple[str, str]:
    """从文件名抽 (date, 需求名)。形如 260706PUSH链路分析 → (2026-07-06, PUSH链路分析)。"""
    stem = Path(name).stem
    m = re.match(r"^(\d{2})(\d{2})(\d{2})", stem)
    if m:
        yy, mm, dd = m.groups()
        return f"20{yy}-{mm}-{dd}", stem[6:].strip() or stem
    return "", stem


def parse_sql_file(text: str, filename: str) -> list[Requirement]:
    """把一个取数脚本文件解析成多条 Requirement（id 留空，由 main 统一编号）。"""
    date, req_name = parse_filename(filename)
    file_meta: dict[str, str] = {}
    records: list[Requirement] = []
    pending: list[str] = []   # 段间注释（尚未归属）
    cur_sql: list[str] = []   # 当前语句的行缓冲
    started = False           # 当前语句是否已出现实质 SQL 内容

    def flush() -> None:
        nonlocal pending, cur_sql, started
        sql = "\n".join(cur_sql).strip()
        if sql:
            if pending:  # 有新描述 → 新记录
                records.append(
                    Requirement(
                        id="",
                        # 去掉标题开头冗余的日期戳（如 "0706 xxx"），date 已单独成字段
                        title=re.sub(r"^\d{4,6}\s+", "", pending[0]).strip(),
                        desc="\n".join(pending),
                        sql=sql,
                        tables=extract_tables(sql),
                        biz_line=file_meta.get("业务线", ""),
                        date=date,
                        author=file_meta.get("需求方", ""),
                        source=req_name,
                    )
                )
            elif records:  # 无新描述 → 并入上一条（如 count 校验 / 导出）
                records[-1].sql += "\n\n" + sql
                for t in extract_tables(sql):
                    if t not in records[-1].tables:
                        records[-1].tables.append(t)
            else:  # 文件开头即 SQL，无注释
                records.append(
                    Requirement(
                        id="", title=req_name, desc="", sql=sql,
                        tables=extract_tables(sql),
                        biz_line=file_meta.get("业务线", ""),
                        date=date, author=file_meta.get("需求方", ""),
                        source=req_name,
                    )
                )
        pending = []
        cur_sql = []
        started = False

    for raw in text.splitlines():
        s = raw.strip()
        if s.startswith("--"):
            body = clean_comment(s)
            mm = META_RE.match(body)
            if mm and not started:  # 文件级元信息
                raw_key = mm.group(1)
                norm = KEY_MAP.get(raw_key) or KEY_MAP.get(raw_key.lower()) or raw_key
                file_meta[norm] = mm.group(2).strip()
                continue
            if not started:  # 段间描述注释
                if body:
                    pending.append(body)
                continue
            cur_sql.append(raw)  # 语句内注释，保留
            continue
        if not s:  # 空行
            if started:
                cur_sql.append(raw)
            continue
        # 实质 SQL 内容行
        started = True
        cur_sql.append(raw)
        if s.endswith(";"):
            flush()

    if cur_sql or pending:  # 收尾（最后一条可能无分号）
        flush()
    return records


def iter_input_files(path: str | Path) -> list[Path]:
    """输入是目录则遍历其中文件（跳过说明文件与隐藏文件）；是文件则返回自身。"""
    p = Path(path)
    skip = {"把样例粘贴到这里.md"}
    if p.is_dir():
        return [
            f for f in sorted(p.iterdir())
            if f.is_file() and not f.name.startswith(".") and f.name not in skip
        ]
    return [p]


def main() -> None:
    import argparse
    import json
    import sys

    ap = argparse.ArgumentParser(description="把取数脚本文档解析成标准 jsonl")
    ap.add_argument(
        "input",
        nargs="?",
        default=str(config.DATA_DIR / "真实样例"),
        help="输入文件或目录（默认 data/真实样例/）",
    )
    ap.add_argument("-o", "--output", default=str(config.JSONL_PATH), help="输出 jsonl 路径")
    args = ap.parse_args()

    files = iter_input_files(args.input)
    all_recs: list[Requirement] = []
    for f in files:
        recs = parse_sql_file(f.read_text(encoding="utf-8", errors="ignore"), f.name)
        print(f"  {f.name} → {len(recs)} 条", file=sys.stderr)
        all_recs.extend(recs)

    for i, r in enumerate(all_recs, 1):  # 统一编号
        r.id = f"req-{i:03d}"

    ok = warn = 0
    with open(args.output, "w", encoding="utf-8") as fo:
        for r in all_recs:
            problems = r.validate()
            if problems:
                warn += 1
                print(f"[warn] {r.id}（{r.title[:16]}）：{'；'.join(problems)}", file=sys.stderr)
            else:
                ok += 1
            fo.write(json.dumps(r.to_dict(), ensure_ascii=False) + "\n")

    print(f"解析完成：{len(all_recs)} 条（来自 {len(files)} 个文件）→ {args.output}（正常 {ok}，警告 {warn}）")
    print("→ 打开 jsonl 核对拆分是否正确，再运行 build_index.py")


if __name__ == "__main__":
    main()
