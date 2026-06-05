#!/usr/bin/env python3
"""创作者签约审核校验 · 一键执行入口

用法：
    python3 run_audit_check.py --batch1 <batch1.csv> --batch2 <batch2.csv> [--output-dir <dir>]

步骤：
    0) 签约名单 → 审核表 推送校验（两批各跑一次）
    1) 审核表 → 内容池 历史入库匹配
    2) 内容池作者 → 签约清单 匹配（含 emoji 容错）

所有 SQL 通过父目录的 run_validate_sql.py（即 data-sql skill 的 sql_query_tool.py）执行。
"""
import argparse
import csv
import os
import subprocess
import sys
import tempfile
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'shared'))

from emoji_clean import strict_clean  # noqa: E402
from gen_contract_values import (  # noqa: E402
    load_batch1, load_batch2, merge_contracts,
    to_values_2col,
)
from paths import SQL_QUERY_TOOL as SQL_TOOL  # noqa: E402

HOST = 'zjyprc'


def run_sql(sql_text):
    """执行 SQL，返回 (stdout, stderr)。大结果会被 sql_query_tool.py 保存到 CSV 文件。"""
    result = subprocess.run(
        ['python3', SQL_TOOL, '--host', HOST, sql_text],
        capture_output=True, text=True, timeout=600,
    )
    return result.stdout, result.stderr


def run_sql_file_with_placeholder(sql_path, values_text, values_placeholder='__CONTRACTS_VALUES__'):
    """读 SQL 模板，替换占位符，执行。"""
    with open(sql_path, encoding='utf-8') as f:
        sql = f.read()
    sql = sql.replace(values_placeholder, values_text)
    return run_sql(sql)


def parse_saved_csv(stdout):
    """从 sql_query_tool 的输出中提取它保存的 CSV 路径（"Saved to ./data_*.csv"）。"""
    for line in stdout.splitlines():
        if 'Saved to' in line:
            # 形如 Result too large (N rows). Saved to ./data_xxx.csv
            path = line.split('Saved to')[-1].strip().rstrip('.').strip()
            return path
    return None


def extract_result_table(stdout):
    """从 stdout 中提取 QUERY RESULT 部分的表格（简单模式）。"""
    lines = stdout.splitlines()
    try:
        start = next(i for i, l in enumerate(lines) if 'QUERY RESULT' in l) + 2
    except StopIteration:
        return ''
    result = []
    for l in lines[start:]:
        if l.startswith('='):
            break
        result.append(l)
    return '\n'.join(result)


def do_step0(batch1_csv, batch2_csv, output_dir):
    """步骤 0：两批签约名单 → 审核表推送校验。"""
    print("\n" + "="*70)
    print("步骤 0 · 签约名单 → 审核表推送校验")
    print("="*70)
    results = {}
    for batch_name, loader, csv_path in [
        ('batch1', load_batch1, batch1_csv),
        ('batch2_cp_name', lambda p: [(cp, n) for _, cp, n in load_batch2(p)], batch2_csv),
    ]:
        if not csv_path:
            print(f"[skip] {batch_name}: no CSV provided")
            continue
        rows = loader(csv_path)
        if not rows:
            print(f"[skip] {batch_name}: empty after exemption filter")
            continue
        values = to_values_2col(rows)
        print(f"\n[{batch_name}] {len(rows)} 条名单，跑汇总...")
        summary_sql = os.path.join(HERE, 'step0_push_check.sql')
        stdout, stderr = run_sql_file_with_placeholder(summary_sql, values)
        print(extract_result_table(stdout))
        # 明细
        print(f"[{batch_name}] 跑未推送明细...")
        detail_sql = os.path.join(HERE, 'step0_push_check_detail.sql')
        stdout, stderr = run_sql_file_with_placeholder(detail_sql, values)
        saved = parse_saved_csv(stdout)
        if saved and os.path.exists(saved):
            dest = os.path.join(output_dir, f'step0_{batch_name}_not_pushed.csv')
            os.rename(saved, dest)
            results[batch_name] = dest
            print(f"  → {dest}")
        else:
            print(f"  (no detail rows or file missing)")
    return results


def do_step1(output_dir):
    """步骤 1：审核表 → 内容池 历史入库匹配。"""
    print("\n" + "="*70)
    print("步骤 1 · 审核表 → 内容池 历史入库匹配")
    print("="*70)
    with open(os.path.join(HERE, 'step1_pool_match.sql'), encoding='utf-8') as f:
        sql = f.read()
    stdout, _ = run_sql(sql)
    print(extract_result_table(stdout))

    # 明细
    print("\n跑从未入库明细...")
    with open(os.path.join(HERE, 'step1_pool_match_detail.sql'), encoding='utf-8') as f:
        sql = f.read()
    stdout, _ = run_sql(sql)
    saved = parse_saved_csv(stdout)
    if saved and os.path.exists(saved):
        dest = os.path.join(output_dir, 'step1_never_in_pool.csv')
        os.rename(saved, dest)
        print(f"  → {dest}")
        return dest
    return None


def do_step2(batch1_csv, batch2_csv, output_dir):
    """步骤 2：内容池作者 → 签约清单 匹配（含 emoji 容错）。"""
    print("\n" + "="*70)
    print("步骤 2 · 内容池作者 → 签约清单 匹配（含 emoji 容错）")
    print("="*70)
    b1 = load_batch1(batch1_csv) if batch1_csv else []
    b2 = load_batch2(batch2_csv) if batch2_csv else []
    merged = merge_contracts(b1, b2)
    print(f"合并签约清单：{len(merged)} 条")
    values = to_values_2col(merged)

    # 汇总（严格精确匹配）
    summary_sql = os.path.join(HERE, 'step2_contract_match.sql')
    stdout, _ = run_sql_file_with_placeholder(summary_sql, values)
    print("\n严格精确匹配结果：")
    print(extract_result_table(stdout))

    # 明细（严格未命中的候选）
    detail_sql = os.path.join(HERE, 'step2_contract_match_detail.sql')
    stdout, _ = run_sql_file_with_placeholder(detail_sql, values)
    saved = parse_saved_csv(stdout)
    if not (saved and os.path.exists(saved)):
        print("严格精确匹配无未命中记录（跳过 emoji 容错步骤）")
        return None, None

    strict_miss_csv = saved
    # Python 做 emoji 容错二次匹配
    return do_emoji_tolerance(strict_miss_csv, merged, output_dir)


def do_emoji_tolerance(strict_miss_csv, merged_contracts, output_dir):
    """对严格匹配未命中的候选，做 emoji/乱码清洗后二次匹配。"""
    # 签约清单：清洗后索引 (cp, cleaned) -> 原名
    contracts_clean = {}
    for cp, name in merged_contracts:
        c = strict_clean(name)
        if c:
            contracts_clean.setdefault((cp, c), []).append(name)

    emoji_matched = []  # 清洗后命中
    truly_miss = []     # 清洗后仍未命中
    with open(strict_miss_csv, encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader, None)
        for r in reader:
            if len(r) < 3:
                continue
            cp, all_names, lid = r[0], r[1], r[2]
            names = [n.strip() for n in all_names.split('|')]
            hit = None
            for n in names:
                c = strict_clean(n)
                if (cp, c) in contracts_clean:
                    hit = (n, c, contracts_clean[(cp, c)][0])
                    break
            if hit:
                n, c, original = hit
                emoji_matched.append((cp, all_names, original, c, lid))
            else:
                truly_miss.append((cp, all_names, lid))

    # 写两个 CSV
    emoji_path = os.path.join(output_dir, 'step2_emoji_matched.csv')
    truly_path = os.path.join(output_dir, 'step2_not_in_contract_final.csv')
    with open(emoji_path, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['cp', 'pool_all_names', 'contract_original_name', 'cleaned', 'lead_author_id'])
        w.writerows(emoji_matched)
    with open(truly_path, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['cp', 'pool_all_names', 'lead_author_id'])
        w.writerows(truly_miss)

    print(f"\nemoji 容错命中：{len(emoji_matched)} 位 → {emoji_path}")
    print(f"真·不在签约清单：{len(truly_miss)} 位 → {truly_path}")

    # 清理临时 CSV
    try:
        os.remove(strict_miss_csv)
    except Exception:
        pass

    return emoji_path, truly_path


def main():
    ap = argparse.ArgumentParser(
        description='创作者签约审核校验',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument('--batch1', help='第一批签约 CSV（列：cp, author_name）')
    ap.add_argument('--batch2', help='第二批签约 CSV（列：...cpapi...author_name...）')
    ap.add_argument('--output-dir', help='输出目录（默认 ~/Desktop/VS Code/签约审核校验_YYYYMMDD/）')
    ap.add_argument('--steps', default='0,1,2', help='要跑的步骤，逗号分隔（默认 0,1,2）')
    args = ap.parse_args()

    if not args.output_dir:
        today = datetime.now().strftime('%Y%m%d')
        args.output_dir = os.path.expanduser(f'~/Desktop/VS Code/签约审核校验_{today}')
    os.makedirs(args.output_dir, exist_ok=True)
    print(f"输出目录：{args.output_dir}")

    steps = set(args.steps.split(','))
    if '0' in steps:
        do_step0(args.batch1, args.batch2, args.output_dir)
    if '1' in steps:
        do_step1(args.output_dir)
    if '2' in steps:
        do_step2(args.batch1, args.batch2, args.output_dir)

    print("\n" + "="*70)
    print("校验完成。下一步可将明细 CSV 同步到飞书表格。")
    print(f"产出目录：{args.output_dir}")
    print("="*70)


if __name__ == '__main__':
    main()