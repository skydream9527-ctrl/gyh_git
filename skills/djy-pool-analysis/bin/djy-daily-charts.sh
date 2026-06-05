#!/usr/bin/env bash
# djy 日报图表 pipeline · 端到端独立脚本
#
# 用法：
#   djy-daily-charts.sh                  # 跑全流程到卡片 JSON 组装，不推送
#   djy-daily-charts.sh --push           # 跑全流程并推送飞书群
#   djy-daily-charts.sh --end 20260501   # 指定结束日期（7 天窗口为 end-6 ~ end）
#   djy-daily-charts.sh --push --end 20260501
#
# 产出：
#   Desktop/ai_djy_pool_analysis/charts/djy_chart_today.html  · 交互 HTML
#   Desktop/ai_djy_pool_analysis/charts/chart_c1~c6.png       · 6 张单图
#   Desktop/ai_djy_pool_analysis/tmp/chart_card_today.json    · 飞书卡片
#
# 未来合入日报 cron：在 djy-daily-report.sh 里合适位置调 `djy-daily-charts.sh --push` 即可。
# 本脚本**不改**现有 daily-report.sh 行为。

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL="$(cd "$SCRIPT_DIR/.." && pwd)"
SCRIPTS="$SKILL/scripts"

# 让 python3 走 venv（与 paths.py 的 PYTHON_CMD 探测保持一致）。
if [ -n "${DJY_PYTHON:-}" ] && [ -x "${DJY_PYTHON}" ]; then
  PATH="$(dirname "$DJY_PYTHON"):$PATH"
elif [ -x "$HOME/djy-deploy/.venv/bin/python" ]; then
  PATH="$HOME/djy-deploy/.venv/bin:$PATH"
fi
export PATH
OUTBASE="$HOME/Desktop/ai_djy_pool_analysis"
CHARTS="$OUTBASE/charts"
TMP="$OUTBASE/tmp"

# -------- 解析参数 --------
PUSH=0
END_DATE=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --push) PUSH=1; shift ;;
    --end) END_DATE="$2"; shift 2 ;;
    *) echo "unknown: $1"; exit 2 ;;
  esac
done
[[ -z "$END_DATE" ]] && END_DATE=$(date +%Y%m%d)

echo "[1/6] 日期窗口由 render_sql 在 SQL 执行时动态注入"
# 2026-05-25 起：chart_stock_trend.sql / chart_daily_trend.sql 改用 {{CUTOFF_N}} /
# {{CUTOFF_ISO_N}} 占位符，由 exempt_lib.render_sql() 在 run_validate_sql.py 内统一展开
# （锚点 T-1，可用 DJY_DATE_ANCHOR=YYYY-MM-DD 覆盖）。原本在此就地改写 SQL 文件的逻辑
# 已废弃；如需指定日期，请用 DJY_DATE_ANCHOR 环境变量。
if [[ "$END_DATE" != "$(date +%Y%m%d)" ]]; then
  # END_DATE 解析为 YYYY-MM-DD 后塞 DJY_DATE_ANCHOR
  ANCHOR_ISO=$(python3 -c "import datetime; print(datetime.datetime.strptime('$END_DATE','%Y%m%d').strftime('%Y-%m-%d'))")
  export DJY_DATE_ANCHOR="$ANCHOR_ISO"
  echo "  DJY_DATE_ANCHOR=$DJY_DATE_ANCHOR (END_DATE=$END_DATE)"
else
  echo "  默认锚点 T-1（昨天）"
fi

echo "[2/6] 跑 SQL"
cd "$SKILL"
STOCK_LOG=$(mktemp)
DAILY_LOG=$(mktemp)
ID_LOG=$(mktemp)
python3 scripts/validate/run_validate_sql.py scripts/validate/chart_stock_trend.sql > "$STOCK_LOG" 2>&1
python3 scripts/validate/run_validate_sql.py scripts/validate/chart_daily_trend.sql > "$DAILY_LOG" 2>&1
python3 scripts/validate/run_validate_sql.py scripts/validate/chart_id_consistency_trend.sql > "$ID_LOG" 2>&1
STOCK_CSV=$(grep -o "Saved to \./[^ ]*\.csv" "$STOCK_LOG" | tail -1 | awk '{print $NF}' | sed "s|^\./|$SKILL/|")
DAILY_CSV=$(grep -o "Saved to \./[^ ]*\.csv" "$DAILY_LOG" | tail -1 | awk '{print $NF}' | sed "s|^\./|$SKILL/|")
ID_CSV=$(grep -o "Saved to \./[^ ]*\.csv" "$ID_LOG" | tail -1 | awk '{print $NF}' | sed "s|^\./|$SKILL/|")
# fallback：skill 目录下的文件会被"file-organize" hook 移到 Desktop
[[ -f "$STOCK_CSV" ]] || STOCK_CSV=$(ls -t "$TMP"/data_*.csv | head -3 | tail -1)
[[ -f "$DAILY_CSV" ]] || DAILY_CSV=$(ls -t "$TMP"/data_*.csv | head -2 | tail -1)
[[ -f "$ID_CSV" ]] || ID_CSV=$(ls -t "$TMP"/data_*.csv | head -1)
echo "  stock_csv: $STOCK_CSV"
echo "  daily_csv: $DAILY_CSV"
echo "  id_csv: $ID_CSV"

echo "[3/6] 生成 HTML"
HTML="$CHARTS/djy_chart_today.html"
python3 "$SCRIPTS/shared/chart_gen_html.py" "$STOCK_CSV" "$DAILY_CSV" "$END_DATE" "$HTML" "" "$ID_CSV"

echo "[4/6] 生成 6 张 PNG"
python3 "$SCRIPTS/shared/chart_html_to_png.py" "$HTML" "$CHARTS"

echo "[5/6] 上传飞书图床 + 组卡片"
IMG_KEYS=()
for i in 1 2 3 4 5 6; do
  K=$(python3 "$SCRIPTS/shared/feishu_upload_image.py" "$CHARTS/chart_c$i.png")
  IMG_KEYS+=("$K")
  echo "  c$i → $K"
done
CARD_JSON="$TMP/chart_card_today.json"
python3 "$SCRIPTS/shared/build_chart_card.py" "$STOCK_CSV" "${IMG_KEYS[@]}" > "$CARD_JSON"
echo "  card JSON: $CARD_JSON"

echo "[6/6] 推送"
if [[ $PUSH -eq 1 ]]; then
  python3 "$SCRIPTS/shared/feishu_post.py" "$CARD_JSON"
  echo "  ✅ 已推送到飞书群"
else
  echo "  ⏸ 未推送（加 --push 才真推）"
fi

echo
echo "完成 · HTML: $HTML"
