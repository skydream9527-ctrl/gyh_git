#!/usr/bin/env python3
"""CONCAT_WS 单列 CSV → 标准多列 CSV 转换器。

用法：
  python3 export_to_csv.py <src.csv> <dst> <col1> <col2> ...

dst 取值规则：
  - 绝对路径 → 原样作为目标路径
  - 相对路径或纯文件名 → 自动拼到 DIRTY_DIR 下
"""
import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "shared"))
from paths import DIRTY_DIR


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)

    src, dst = sys.argv[1], sys.argv[2]
    if not os.path.isabs(dst):
        dst = str(DIRTY_DIR / dst)
    headers = sys.argv[3:]
    n = len(headers)

    with open(src) as f_in, open(dst, "w", newline="") as f_out:
        w = csv.writer(f_out)
        w.writerow(headers)
        next(f_in)
        kept = dropped = 0
        for line in f_in:
            parts = line.rstrip("\n").split("\x01")
            if len(parts) == n:
                w.writerow(parts)
                kept += 1
            else:
                dropped += 1
    print(f"{kept} rows -> {dst}" + (f"  ({dropped} rows dropped due to column mismatch)" if dropped else ""))


if __name__ == "__main__":
    main()
