#!/bin/bash
# djy 内容池校验日报 · 纯 bash 版（2026-05-12 起代替 claude headless 编排）
# 单次跑完整 10 步流程；不依赖 Claude LLM，全流程 bash + python 脚本调用。
#
# 用法:
#   bash djy-daily-run.sh                     # 默认: 数据锚 T-1, 跑完 + 推飞书
#   bash djy-daily-run.sh --skip-push         # 不推飞书（手动验证/归档场景）
#   bash djy-daily-run.sh --yesterday 20260511 # 补跑指定日期
#
# 退出码：
#   0 = 全部成功（DONE）
#   非 0 = 某步失败（stderr 有具体步骤名）

set -euo pipefail

# === 参数解析 ===
SKIP_PUSH=0
YESTERDAY_OVERRIDE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --skip-push) SKIP_PUSH=1; shift ;;
    --yesterday) YESTERDAY_OVERRIDE="$2"; shift 2 ;;
    -h|--help)
      grep '^#' "$0" | head -20
      exit 0
      ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

# === 路径变量 ===
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL="$(cd "$SCRIPT_DIR/.." && pwd)"

# 让 python3 走 venv（与 paths.py 的 PYTHON_CMD 探测保持一致）。
# cron 不 source .bashrc，PATH 里没有 venv，必须显式注入。
if [ -n "${DJY_PYTHON:-}" ] && [ -x "${DJY_PYTHON}" ]; then
  PATH="$(dirname "$DJY_PYTHON"):$PATH"
elif [ -x "$HOME/djy-deploy/.venv/bin/python" ]; then
  PATH="$HOME/djy-deploy/.venv/bin:$PATH"
fi
export PATH

ROOT="${DJY_OUTPUT_ROOT:-$HOME/ai_djy_pool_analysis}"
TODAY=$(date +%Y%m%d)
if [ -n "$YESTERDAY_OVERRIDE" ]; then
  YESTERDAY="$YESTERDAY_OVERRIDE"
else
  YESTERDAY=$(date -v-1d +%Y%m%d 2>/dev/null || date -d "1 days ago" +%Y%m%d)
fi
REPORTS="$ROOT/daily_reports"
REPORT_PATH="$REPORTS/${TODAY}.json"
HTML_PATH="$ROOT/reports/content_pool_validate_${YESTERDAY}.html"
CHART_DIR="$ROOT/charts/${TODAY}"
REPORT_URL="http://ai-djy-pool-analysis-4bbd9e.pages.n.xiaomi.com/content_pool_validate_${YESTERDAY}.html"

# === 加载 .env（FEISHU_WEBHOOK / SECRET / APP_ID / APP_SECRET）===
if [ -f "$SKILL/.env" ]; then
  set -a
  . "$SKILL/.env"
  set +a
fi
PROJECT_ENV="$(cd "$SKILL/../.." && pwd)/.env"
if [ -f "$PROJECT_ENV" ]; then
  set -a
  . "$PROJECT_ENV"
  set +a
fi

ts() { date '+%H:%M:%S'; }
step() { echo "[$(ts)] Step $1 · $2"; }
die() { echo "[$(ts)] FAILED at Step $1: $2" >&2; exit 1; }

echo "=========================================="
echo "djy-daily-run · TODAY=$TODAY YESTERDAY=$YESTERDAY skip_push=$SKIP_PUSH"
echo "=========================================="

# --- Step 1 · 跑消费数据 -----------------------------------------------------
# 不再用 `2>&1 | tail -1` 吞 stderr：那样 [FATAL] / [long-runner] / [upstream-wait]
# 进度全丢，cron 失败时只剩 .err=0bytes 没线索可查（5-29、6-1 都因此盲调）。
# 把 stderr 转发到 runner stdout（被 cron logger tee 到 .log），stdout 单独捕获 JSON 路径。
step 1 "跑消费数据 (T-1=$YESTERDAY)"
CONSUM_ERR="$ROOT/tmp/consumption_${YESTERDAY}_stderr.log"
CONSUM_JSON=$(python3 "$SKILL/scripts/consumption/consumption_daily_card.py" --date "$YESTERDAY" 2>"$CONSUM_ERR") || {
  echo "--- consumption stderr ---"
  cat "$CONSUM_ERR"
  echo "--- end consumption stderr ---"
  die 1 "consumption_daily_card failed (see stderr above)"
}
[ -s "$CONSUM_ERR" ] && { echo "--- consumption stderr ---"; cat "$CONSUM_ERR"; echo "--- end consumption stderr ---"; }
rm -f "$CONSUM_ERR"
[ -f "$CONSUM_JSON" ] || die 1 "consumption json not found: $CONSUM_JSON"
echo "   CONSUM_JSON=$CONSUM_JSON"

# --- Step 2 · 校验 template_a / rule21（抑制清单已排除 rule20）--------------
# 2026-05-25: template_a_stock 切到 run_long_validate_sql.py（pyhive 直连 900s）。
#             之前走 sql_query_tool 250s 硬限，集群慢就被砍（今天日报挂的就是这条）。
#             rule21 是快查询，保留 sql_query_tool 路径。
step 2 "校验 template_a_stock + rule21"
cd "$SKILL"
python3 scripts/validate/run_long_validate_sql.py scripts/validate/template_a_stock.sql 2>&1 | tail -15 || die 2 "template_a_stock failed"
python3 scripts/validate/run_validate_sql.py scripts/validate/rule21_item_id_dedup.sql | tail -10 || die 2 "rule21_item_id_dedup failed"

# --- Step 3 · 趋势 stock_trend + daily_trend --------------------------------
# 2026-05-15: stock_trend / daily_trend 改用 run_long_validate_sql.py 跑（pyhive 直连，
# 900s polling timeout）。原 run_validate_sql 走 sql_query_tool 是 250s 客户端硬限，
# 重查询服务端真正只要 ~200s 但被客户端误杀。
step 3 "趋势 stock_trend"
set +e
STOCK_OUT=$(python3 scripts/validate/run_long_validate_sql.py scripts/validate/chart_stock_trend.sql 2>&1)
RC=$?
set -e
# tail 30：保留 2026-05-14 的诊断盲区修复
echo "$STOCK_OUT" | tail -30
[ $RC -eq 0 ] || die 3 "chart_stock_trend rc=$RC"
STOCK_CSV="$ROOT/tmp/$(echo "$STOCK_OUT" | grep -oE 'data_[0-9]+\.csv' | tail -1)"
[ -f "$STOCK_CSV" ] || die 3 "stock csv not saved: $STOCK_CSV"
echo "   STOCK_CSV=$STOCK_CSV"

step 3.5 "趋势 daily_trend"
set +e
DAILY_OUT=$(python3 scripts/validate/run_long_validate_sql.py scripts/validate/chart_daily_trend.sql 2>&1)
RC=$?
set -e
echo "$DAILY_OUT" | tail -30
[ $RC -eq 0 ] || die 3 "chart_daily_trend rc=$RC"
DAILY_CSV="$ROOT/tmp/$(echo "$DAILY_OUT" | grep -oE 'data_[0-9]+\.csv' | tail -1)"
[ -f "$DAILY_CSV" ] || die 3 "daily csv not saved: $DAILY_CSV"
echo "   DAILY_CSV=$DAILY_CSV"

# --- Step 3.6 · 趋势 三元 ID 一致性（cp_author 多 xm / lead 多 cp）-----------
# 2026-05-26 新增：在线池里 cp_author 挂多 xm + lead 挂多 cp_author 的趋势数据
# 输出 4 列 CSV (snap_date, a_cp, multi_xm_authors_n, multi_cp_leads_n)，
# chart_gen_html.py 把 2 个 *_n 字段合入 c3~c6 per-CP 趋势曲线
step 3.6 "趋势 id_consistency_trend"
set +e
ID_OUT=$(python3 scripts/validate/run_long_validate_sql.py scripts/validate/chart_id_consistency_trend.sql 2>&1)
RC=$?
set -e
echo "$ID_OUT" | tail -10
[ $RC -eq 0 ] || die 3 "chart_id_consistency_trend rc=$RC"
ID_CSV="$ROOT/tmp/$(echo "$ID_OUT" | grep -oE 'data_[0-9]+\.csv' | tail -1)"
[ -f "$ID_CSV" ] || die 3 "id_consistency csv not saved: $ID_CSV"
echo "   ID_CSV=$ID_CSV"

# --- Step 4 · 生成 HTML 报告 ------------------------------------------------
step 4 "生成 HTML"
python3 "$SKILL/scripts/shared/chart_gen_html.py" \
  "$STOCK_CSV" "$DAILY_CSV" "$YESTERDAY" "$HTML_PATH" "$CONSUM_JSON" "$ID_CSV" \
  || die 4 "chart_gen_html failed"
echo "   HTML_PATH=$HTML_PATH"

# --- Step 5 · 截整页长图 ----------------------------------------------------
step 5 "截整页长图"
mkdir -p "$CHART_DIR"
LONGPNG="$CHART_DIR/daily_${YESTERDAY}_$(date +%H%M%S).png"
python3 "$SKILL/scripts/shared/chart_html_to_longpng.py" "$HTML_PATH" "$LONGPNG" \
  || die 5 "chart_html_to_longpng failed"
echo "   LONGPNG=$LONGPNG ($(du -h "$LONGPNG" | awk '{print $1}'))"

# --- Step 6 · 上传飞书图床 --------------------------------------------------
step 6 "上传飞书图床"
IMG_KEY=$(python3 "$SKILL/scripts/shared/feishu_upload_image.py" "$LONGPNG") \
  || die 6 "feishu_upload_image failed"
echo "   IMG_KEY=$IMG_KEY"

# --- Step 7 · Push HTML 到 GitLab（飞书链接前置条件） -----------------------
# 同步 remote：cron checkout 不会主动 pull，远端可能已有 hotfix（5-31 cron 就是这样挂的）
# fetch+rebase 必须在 commit 之前；reports/ 文件按日期命名，不会与历史 commit 冲突。
step 7 "git push HTML"
cd "$ROOT"
git fetch origin main 2>&1 | tail -3 || die 7 "git fetch failed"
git rebase origin/main 2>&1 | tail -10 || die 7 "git rebase failed (manual resolution needed)"
git add "reports/content_pool_validate_${YESTERDAY}.html"
HTML_JUST_PUSHED=0
if git diff --cached --quiet; then
  echo "   (html already pushed, skip commit)"
else
  git -c commit.gpgsign=false commit -m "daily: ${YESTERDAY} html report (run on ${TODAY}, T-1 anchored)" \
    || die 7 "git commit failed"
  git push origin main || die 7 "git push failed"
  HTML_JUST_PUSHED=1
fi

# --- Step 7.5 · 等 GitLab Pages 发布就绪（飞书卡片推送前的门禁）-------------
# 为什么：Pages 构建需要 30s-2min，直接推飞书则卡片里的链接可能还是老版本或 404。
# 验证方式：
#   1) 若本次刚 push HTML：先等 45s buffer 让 GitLab CI 启动 + 基本构建
#   2) 轮询 URL HTTP 状态码，200（已登录场景）或 302（auth 重定向，资源存在）视为可达
# 限制：Pages 站点开启了小米 SSO，外部脚本拿不到 HTML 内容，无法 grep 内容校验"新版"。
#   若未来获取到 GITLAB_TOKEN，可升级为查 pipeline `status=success`。
step 7.5 "等 GitLab Pages 发布"
WAIT_MAX=180
WAIT_SEC=0
if [ "$HTML_JUST_PUSHED" -eq 1 ]; then
  echo "   刚 push HTML，先等 45s 让 GitLab CI 启动 + 构建..."
  sleep 45
  WAIT_SEC=45
fi
while true; do
  HTTP_CODE=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 10 "$REPORT_URL" 2>/dev/null || echo "000")
  if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "302" ]; then
    echo "   Pages 可达 (HTTP $HTTP_CODE) at ${WAIT_SEC}s · $REPORT_URL"
    break
  fi
  if [ "$WAIT_SEC" -ge "$WAIT_MAX" ]; then
    die 7.5 "Pages 未在 ${WAIT_MAX}s 内可达（last HTTP=$HTTP_CODE），URL=$REPORT_URL"
  fi
  sleep 10
  WAIT_SEC=$((WAIT_SEC + 10))
  [ $((WAIT_SEC % 30)) -eq 0 ] && echo "   still waiting Pages (${WAIT_SEC}s/${WAIT_MAX}s, last HTTP=$HTTP_CODE)..."
done

# --- Step 8 · 组装「长图版」卡片 JSON --------------------------------------
step 8 "组装卡片 JSON"
python3 "$SKILL/scripts/shared/build_longpng_card.py" \
    --image-key "$IMG_KEY" \
    --date "$YESTERDAY" \
    --report-url "$REPORT_URL" \
    > "$REPORT_PATH" \
  || die 8 "build_longpng_card failed"
echo "   REPORT_PATH=$REPORT_PATH"

# --- Step 9 · 推送飞书（可跳过）--------------------------------------------
if [ "$SKIP_PUSH" -eq 1 ]; then
  step 9 "推送飞书 · SKIP (因 --skip-push)"
else
  step 9 "推送飞书"
  set +e
  python3 "$SKILL/scripts/shared/feishu_post.py" "$REPORT_PATH"
  PUSH_RC=$?
  set -e
  if [ $PUSH_RC -ne 0 ]; then
    rm -f "$REPORT_PATH"
    die 9 "feishu_post rc=$PUSH_RC"
  fi
fi

# --- Step 10 · Push daily artifacts ----------------------------------------
step 10 "git push daily artifacts"
bash "$SKILL/scripts/shared/git_push_daily.sh" "$TODAY" || die 10 "git_push_daily failed"

echo "=========================================="
echo "DONE · $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="
