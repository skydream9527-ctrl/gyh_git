"""命令行检索入口。

示例：
  python search.py "按城市统计每日新增用户"
  python search.py "短剧留存" --k 3
  python search.py "圈选push人群" --biz-line 增长
  python search.py "按城市统计新增" --json       # 输出 JSON，供下游程序消费
  python search.py "按城市统计新增" --fewshot    # 输出可喂给 LLM 的 few-shot prompt
"""
from __future__ import annotations

import argparse
import json

import retriever


def main() -> None:
    ap = argparse.ArgumentParser(description="检索历史相似需求及其 SQL")
    ap.add_argument("query", help="新需求的自然语言描述")
    ap.add_argument("--k", type=int, default=None, help="返回条数（默认见 config.TOP_K）")
    ap.add_argument("--biz-line", default=None, help="按业务线过滤")
    ap.add_argument("--json", action="store_true", help="输出 JSON（供下游程序消费）")
    ap.add_argument("--fewshot", action="store_true", help="输出可喂给 LLM 的 few-shot prompt")
    args = ap.parse_args()

    filters = {"biz_line": args.biz_line} if args.biz_line else None
    results = retriever.retrieve(args.query, k=args.k, filters=filters)

    if args.fewshot:
        print(retriever.build_fewshot_prompt(args.query, results))
        return
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return

    if not results:
        print("没有检索到相似需求。")
        return
    for i, r in enumerate(results, 1):
        meta = " ".join(x for x in [r.get("biz_line", ""), r.get("date", "")] if x)
        print(f"\n{'=' * 64}")
        print(f"[{i}] {r['title']}  （{meta}）")
        if r.get("tables"):
            print(f"表：{', '.join(r['tables'])}")
        print(f"描述：{r['desc']}")
        print(f"SQL：\n{r['sql']}")


if __name__ == "__main__":
    main()
