"""从签约名单 CSV 生成 SQL VALUES 子句。

签约名单 CSV 格式：
- 第一批（简单）：cp, author_name
- 第二批（含 xm_author_id）：xm_author_id, cp, author_name
"""
import csv
import sys


EXCLUDED_CP = {'cn-meilaoban-djy'}  # 豁免：媒老板整家未推送


def escape(s):
    """Trino 字符串转义：单引号加倍。"""
    return (s or '').replace("'", "''")


def load_batch1(path):
    """第一批 CSV -> [(cp, name)]，已去重并排除媒老板。"""
    rows = set()
    with open(path, encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader, None)
        for r in reader:
            if len(r) < 2:
                continue
            cp, name = r[0].strip(), r[1].strip()
            if not cp or not name:
                continue
            if cp in EXCLUDED_CP:
                continue
            rows.add((cp, name))
    return sorted(rows)


def load_batch2(path):
    """第二批 CSV -> [(xm_author_id, cp, name)]，已去重并排除媒老板。

    第二批列顺序：author_id, xm_author_id, top_category, contents, expos_cnt,
    click_cnt, consum_dura, positive_cnt, cpapi, authors, author_name, ...
    若列名不符，fallback 按位置取第 1/8/10 列。
    """
    rows = set()
    with open(path, encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader, None) or []
        # 尝试按列名定位
        try:
            idx_xm = header.index('xm_author_id')
            idx_cp = header.index('cpapi')
            idx_name = header.index('author_name')
        except ValueError:
            idx_xm, idx_cp, idx_name = 1, 8, 10  # 按位置兜底
        for r in reader:
            if len(r) <= max(idx_xm, idx_cp, idx_name):
                continue
            xm = r[idx_xm].strip()
            cp = r[idx_cp].strip()
            name = r[idx_name].strip()
            if not cp or not name:
                continue
            if cp in EXCLUDED_CP:
                continue
            rows.add((xm, cp, name))
    return sorted(rows)


def merge_contracts(batch1_rows, batch2_rows):
    """合并两批 (cp, name)，去重。"""
    merged = set(batch1_rows)
    for _, cp, name in batch2_rows:
        merged.add((cp, name))
    return sorted(merged)


def to_values_2col(rows):
    """[(cp, name)] -> '(cp, name), (cp, name), ...' 字符串"""
    return ',\n  '.join(f"('{cp}', '{escape(name)}')" for cp, name in rows)


def to_values_3col(rows):
    """[(xm, cp, name)] -> '(xm, cp, name), ...' 字符串"""
    return ',\n  '.join(
        f"('{escape(xm)}', '{cp}', '{escape(name)}')"
        for xm, cp, name in rows
    )


def main():
    import argparse
    ap = argparse.ArgumentParser(description='生成签约名单 SQL VALUES')
    ap.add_argument('--batch1', help='第一批 CSV 路径（列：cp, author_name）')
    ap.add_argument('--batch2', help='第二批 CSV 路径（列：..., cpapi, ..., author_name, ...）')
    ap.add_argument('--mode', choices=['batch1', 'batch2', 'merged'], default='merged',
                    help='输出哪一批；merged = 两批合并去重 (cp, name)')
    args = ap.parse_args()

    if args.mode == 'batch1':
        if not args.batch1:
            print("error: --batch1 required", file=sys.stderr); sys.exit(2)
        print(to_values_2col(load_batch1(args.batch1)))
    elif args.mode == 'batch2':
        if not args.batch2:
            print("error: --batch2 required", file=sys.stderr); sys.exit(2)
        print(to_values_3col(load_batch2(args.batch2)))
    else:
        b1 = load_batch1(args.batch1) if args.batch1 else []
        b2 = load_batch2(args.batch2) if args.batch2 else []
        print(to_values_2col(merge_contracts(b1, b2)))


if __name__ == '__main__':
    main()
