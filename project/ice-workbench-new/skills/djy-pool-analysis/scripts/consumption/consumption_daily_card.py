#!/usr/bin/env python3
"""消费日报卡片生成 · 查数据 → 计算环比 → 输出 JSON

用法：
  python3 consumption_daily_card.py [--date YYYYMMDD] [--print-only]

默认查昨天数据（T+1 产出），输出 JSON 路径到 stdout。
"""
import csv
import datetime
import os
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "shared"))
from paths import TMP_DIR, PYTHON_CMD

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

CPS = "('cn-dihui-djy','cn-beike-djy','cn-guoying-djy','cn-meilaoban-djy')"

# 走 long-runner（pyhive 直连 + 900s polling timeout + transient 模式重试，含 kyuubi
# Invalid OperationHandle / PENDING_STATE 等）。原 sql_query_tool 路径 250s 客户端硬限，
# kyuubi 冷启动经常被误杀（5-29、6-1 cron 失败都是这条）。trend SQL 早就迁过去了。
LONG_RUNNER = os.path.normpath(
    os.path.join(SCRIPT_DIR, "..", "validate", "run_long_validate_sql.py")
)

# dwm_djy_dau_user_consum_index_di 上游 ETL 偶尔延迟（5-30 周六实测延迟 ~48min）。
# T 当天 cp_data 全 None 时不要直接 exit，而是按小时重查，最多再等 2 小时。
# watchdog（djy-daily-report.sh）已对应放宽到 3 小时。
UPSTREAM_WAIT_INTERVAL_SEC = 3600
UPSTREAM_WAIT_MAX_RETRIES = 2


def run_sql(sql: str) -> str:
    """通过 long-runner 执行 SQL。失败由 long-runner 自己重试 transient（30/60s 退避，
    900s polling timeout），返回非 0 即真失败。"""
    with tempfile.NamedTemporaryFile(
        "w", suffix=".sql", dir=str(TMP_DIR), delete=False, encoding="utf-8"
    ) as f:
        f.write(sql)
        sql_path = f.name
    try:
        result = subprocess.run(
            [*PYTHON_CMD, LONG_RUNNER, sql_path],
            cwd=str(TMP_DIR),
            capture_output=True,
            text=True,
        )
        # long-runner 把 [long-runner] 进度日志写 stderr，转发到调用方 stderr 方便排查
        if result.stderr:
            sys.stderr.write(result.stderr)
        if result.returncode != 0:
            sys.stderr.write(
                f"SQL FAILED via long-runner (rc={result.returncode}); stdout: {result.stdout[:300]}\n"
            )
            sys.exit(1)
        return result.stdout
    finally:
        try:
            os.unlink(sql_path)
        except OSError:
            pass


def parse_csv_output(output: str) -> list:
    import re
    # 优先：从 "Saved to ./data_<ts>.csv" 行抽路径，并到 TMP_DIR 下找
    m = re.search(r"Saved to (?:\./)?(data_\d+\.csv)", output)
    if m:
        fname = m.group(1)
        for cand in [str(TMP_DIR / fname), os.path.join(".", fname), fname]:
            if os.path.isfile(cand):
                with open(cand, "r", encoding="utf-8") as f:
                    return list(csv.DictReader(f))
    # 兼容旧格式：整行就是路径
    for line in output.splitlines():
        if line.strip().endswith(".csv") and os.path.isfile(line.strip()):
            with open(line.strip(), "r", encoding="utf-8") as f:
                return list(csv.DictReader(f))

    lines = output.strip().splitlines()
    header_idx = None
    for i, line in enumerate(lines):
        if "QUERY RESULT" in line or "====" in line:
            continue
        stripped = line.strip()
        if stripped and not stripped.startswith("="):
            header_idx = i
            break

    if header_idx is None:
        return []

    header_line = lines[header_idx]
    headers = header_line.split()

    rows = []
    for line in lines[header_idx + 1:]:
        stripped = line.strip()
        if not stripped or stripped.startswith("="):
            continue
        values = stripped.split()
        if len(values) == len(headers):
            rows.append(dict(zip(headers, values)))
        elif len(values) > len(headers):
            row = {}
            row[headers[0]] = values[0]
            for j in range(1, len(headers)):
                row[headers[j]] = values[j]
            rows.append(row)
    return rows


def query_cp_metrics(target_date: str) -> list:
    """查 31 天数据：T、T-1、T-2、…、T-30
    用途：T vs T-1 = 环比；T vs T-7 = 周同比；T-29 ~ T 共 30 天 = 趋势图"""
    end = datetime.datetime.strptime(target_date, "%Y%m%d")
    days = [(end - datetime.timedelta(days=i)).strftime("%Y%m%d") for i in range(31)]
    days_in = ", ".join(f"'{d}'" for d in days)
    sql = f"""SELECT
    item_cp_name,
    date,
    SUM(consum_pv) AS vv,
    ROUND(SUM(consum_dura), 2) AS consum_dura_min,
    COUNT(DISTINCT CASE WHEN expose_pv > 0 THEN item_id END) AS distribute_content_cnt,
    COUNT(DISTINCT CASE WHEN expose_pv > 0 THEN item_author_id END) AS distribute_author_cnt,
    ROUND(SUM(consum_pv) * 1.0 / NULLIF(COUNT(DISTINCT CASE WHEN expose_pv > 0 THEN item_id END), 0), 1) AS vv_per_item,
    ROUND(SUM(consum_dura) / NULLIF(SUM(consum_pv), 0) * 60, 1) AS dura_per_vv_sec
FROM iceberg_zjyprc_hadoop.browser.dwm_djy_dau_user_consum_index_di
WHERE date IN ({days_in})
    AND item_cp_name IN {CPS}
GROUP BY item_cp_name, date
ORDER BY item_cp_name, date"""
    output = run_sql(sql)
    return parse_csv_output(output)


def query_top5(yesterday: str, order_col: str) -> list:
    """Top5 内容：消费表聚合 + 二次查内容池 url 字段用于跳转。
    分两步是因为跨 iceberg/paimon 的 JOIN 在 data-sql 上会退化得很慢。"""
    sql = f"""SELECT item_id, item_title, item_cp_name, item_type,
    SUM(consum_pv) AS vv,
    ROUND(SUM(consum_dura), 2) AS consum_dura_min
FROM iceberg_zjyprc_hadoop.browser.dwm_djy_dau_user_consum_index_di
WHERE date = '{yesterday}'
    AND item_cp_name IN {CPS}
GROUP BY item_id, item_title, item_cp_name, item_type
ORDER BY {order_col} DESC
LIMIT 5"""
    output = run_sql(sql)
    items = parse_csv_output(output)
    if not items:
        return items
    # 二次查 url
    ids = ",".join(f"'{it['item_id']}'" for it in items)
    url_sql = f"""SELECT a_item_id, MAX(url) AS url
FROM paimon_zjyprc_hadoop.browser.business_content_pool_realtime
WHERE a_item_id IN ({ids})
GROUP BY a_item_id"""
    try:
        url_rows = parse_csv_output(run_sql(url_sql))
        url_map = {r["a_item_id"]: r.get("url") for r in url_rows}
        for it in items:
            it["url"] = url_map.get(it["item_id"]) or ""
    except Exception as e:
        print(f"  url 查询失败（忽略）: {e}", file=sys.stderr)
        for it in items:
            it["url"] = ""
    return items


def calc_pct(today_val, yest_val):
    if today_val is None or yest_val is None:
        return None
    try:
        t = float(today_val)
        y = float(yest_val)
    except (ValueError, TypeError):
        return None
    if y == 0 or t != t or y != y:
        return None
    return (t - y) / y * 100


def build_cp_data(rows: list, target_date: str) -> list:
    """从 8 天 rows 构建 cp_data（含 T、环比 T-1、周同比 T-7）"""
    end = datetime.datetime.strptime(target_date, "%Y%m%d")
    day_before = (end - datetime.timedelta(days=1)).strftime("%Y%m%d")
    week_ago = (end - datetime.timedelta(days=7)).strftime("%Y%m%d")

    by_cp = {}
    for r in rows:
        cp = r.get("item_cp_name", "")
        d = r.get("date", "")
        by_cp.setdefault(cp, {})[d] = r

    # (val_key, dod_pct_key, wow_pct_key)
    metrics = [
        ("vv", "vv_pct", "vv_wow_pct"),
        ("consum_dura_min", "dura_pct", "dura_wow_pct"),
        ("distribute_content_cnt", "content_pct", "content_wow_pct"),
        ("distribute_author_cnt", "author_pct", "author_wow_pct"),
        ("vv_per_item", "vv_item_pct", "vv_item_wow_pct"),
        ("dura_per_vv_sec", "dura_vv_pct", "dura_vv_wow_pct"),
    ]

    cp_order = ["cn-dihui-djy", "cn-beike-djy", "cn-guoying-djy", "cn-meilaoban-djy"]
    result = []
    for cp in cp_order:
        if cp not in by_cp:
            continue
        today = by_cp[cp].get(target_date, {})
        prev = by_cp[cp].get(day_before, {})
        week_prev = by_cp[cp].get(week_ago, {})
        item = {"cp": cp}
        for val_key, dod_key, wow_key in metrics:
            t_val = today.get(val_key)
            p_val = prev.get(val_key)
            w_val = week_prev.get(val_key)
            try:
                item[val_key] = float(t_val) if t_val is not None else None
            except (ValueError, TypeError):
                item[val_key] = None
            item[dod_key] = calc_pct(t_val, p_val)
            item[wow_key] = calc_pct(t_val, w_val)
        result.append(item)
    return result


def build_cp_trend_30d(rows: list, target_date: str) -> dict:
    """30 天每日趋势：{cp: {metric: [d29, d28, ..., d0]}} 按 T-29 → T 顺序排"""
    end = datetime.datetime.strptime(target_date, "%Y%m%d")
    day_keys = [(end - datetime.timedelta(days=29 - i)).strftime("%Y%m%d") for i in range(30)]
    day_labels = [(end - datetime.timedelta(days=29 - i)).strftime("%m-%d") for i in range(30)]

    by_cp = {}
    for r in rows:
        cp = r.get("item_cp_name", "")
        d = r.get("date", "")
        by_cp.setdefault(cp, {})[d] = r

    metric_keys = ["vv", "consum_dura_min", "distribute_content_cnt",
                   "distribute_author_cnt", "vv_per_item", "dura_per_vv_sec"]

    cp_order = ["cn-dihui-djy", "cn-beike-djy", "cn-guoying-djy", "cn-meilaoban-djy"]
    result = {"dates": day_labels, "cp": {}}
    for cp in cp_order:
        if cp not in by_cp:
            continue
        cp_series = {}
        for mk in metric_keys:
            series = []
            for d in day_keys:
                v = by_cp[cp].get(d, {}).get(mk)
                try:
                    series.append(float(v) if v is not None else 0)
                except (ValueError, TypeError):
                    series.append(0)
            cp_series[mk] = series
        result["cp"][cp] = cp_series
    return result


def main():
    args = sys.argv[1:]
    print_only = "--print-only" in args

    target_date = None
    for i, a in enumerate(args):
        if a == "--date" and i + 1 < len(args):
            target_date = args[i + 1]

    if target_date is None:
        target_date = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y%m%d")

    date_display = f"{target_date[:4]}-{target_date[4:6]}-{target_date[6:]}"

    cp_rows = None
    cp_data = None
    for attempt in range(UPSTREAM_WAIT_MAX_RETRIES + 1):
        print(
            f"[1/4] 查询 CP 维度指标 (31 天窗口，T={target_date}, attempt {attempt + 1}/{UPSTREAM_WAIT_MAX_RETRIES + 1})...",
            file=sys.stderr,
        )
        cp_rows = query_cp_metrics(target_date)
        cp_data = build_cp_data(cp_rows, target_date)
        # cp_data 列表为空 = SQL 引擎层失败（query 本身没返回任何数据）。
        # 此时不是上游延迟，是 SQL 路径完全断了，没必要等。
        if not cp_data:
            sys.stderr.write(
                "[FATAL] cp_data is empty after query_cp_metrics — likely SQL engine transient failure.\n"
            )
            sys.exit(1)
        # cp_data 列表非空但 T 当天所有 CP 的 vv 都是 None = dwm 上游 ETL 延迟（5-30 周六实测）。
        if any(c.get("vv") is not None for c in cp_data):
            if attempt > 0:
                sys.stderr.write(f"  [upstream-wait] 数据已就绪 (attempt {attempt + 1})\n")
            break
        if attempt >= UPSTREAM_WAIT_MAX_RETRIES:
            sys.stderr.write(
                f"[FATAL] dwm upstream still not ready after {UPSTREAM_WAIT_MAX_RETRIES + 1} attempts "
                f"(~{UPSTREAM_WAIT_MAX_RETRIES} hours of waiting); giving up\n"
            )
            sys.exit(1)
        sys.stderr.write(
            f"  [upstream-wait] T={target_date} 所有 CP vv 全 None，等 "
            f"{UPSTREAM_WAIT_INTERVAL_SEC // 60}min 后重查\n"
        )
        time.sleep(UPSTREAM_WAIT_INTERVAL_SEC)
    cp_trend_30d = build_cp_trend_30d(cp_rows, target_date)

    print("[2/4] 查询 Top5 VV...", file=sys.stderr)
    top5_vv = query_top5(target_date, "vv")

    print("[3/4] 查询 Top5 消费时长...", file=sys.stderr)
    top5_dura = query_top5(target_date, "consum_dura_min")

    for item in top5_vv + top5_dura:
        for k in ("vv", "consum_dura_min"):
            try:
                item[k] = float(item[k])
            except (ValueError, TypeError, KeyError):
                pass

    print("[4/4] 输出 JSON...", file=sys.stderr)
    output = {
        "cp_data": cp_data,
        "cp_trend_30d": cp_trend_30d,
        "top5_vv": top5_vv,
        "top5_dura": top5_dura,
        "report_date": date_display,
    }

    import json
    json_path = str(TMP_DIR / f"consumption_{target_date}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"JSON: {json_path}", file=sys.stderr)
    print(json_path)


if __name__ == "__main__":
    main()
