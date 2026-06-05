#!/bin/bash
# djy 内容池校验日报 · 定时任务包装脚本
# 触发：launchd Mon-Fri 09:45
# 流程：调 djy-daily-run.sh 纯 bash 流水线（2026-05-12 起代替旧的 claude headless 编排）
#
# 调试：手动运行 `bash ~/bin/djy-daily-report.sh` 即可干跑一次

set -u  # 未定义变量报错（但不要 set -e，我们要自己判断失败）

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DAILY_RUN="$SCRIPT_DIR/djy-daily-run.sh"
ALERT_SCRIPT="$SCRIPT_DIR/djy-daily-alert.sh"
LOG_DIR="$HOME/logs/djy-daily"
SKILL_ENV="$SKILL_ROOT/.env"
PROJECT_ENV="$(cd "$SKILL_ROOT/../.." && pwd)/.env"
TODAY=$(date "+%Y-%m-%d")
LOG_FILE="${LOG_DIR}/${TODAY}.log"
# 当日日报 JSON（与 djy-daily-run.sh 中 REPORT_PATH 对齐）。失败兜底清理用。
REPORT_PATH="${DJY_OUTPUT_ROOT:-$HOME/ai_djy_pool_analysis}/daily_reports/$(date +%Y%m%d).json"

# 确保 PATH 里有常见目录（cron/launchd 启动环境很裸）
export PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin:${PATH:-}"

# 加载 skill .env + 项目根 .env；App 凭据统一以项目根配置为准。
if [ -f "$SKILL_ENV" ]; then
  set -a
  . "$SKILL_ENV"
  set +a
fi
if [ -f "$PROJECT_ENV" ]; then
  set -a
  . "$PROJECT_ENV"
  set +a
fi

mkdir -p "$LOG_DIR"

{
  echo "=========================================="
  echo "djy daily report · $(date '+%Y-%m-%d %H:%M:%S')"
  echo "=========================================="

  # 预检：runner 脚本存在可执行
  if [ ! -x "$DAILY_RUN" ]; then
    echo "FAILED: runner script missing or not executable: $DAILY_RUN"
    "$ALERT_SCRIPT" "runner 脚本缺失或无执行权限" "$LOG_FILE"
    exit 1
  fi

  cd "$HOME"

  # 3 小时 watchdog：~25min SQL pipeline + 最长 2h 上游 ETL 等待（5-30 周六实测延迟 ~48min）
  # + 余量。上游延迟由 consumption_daily_card.py 内部小时级 poll 等待（最多 2 次重试）。
  TIMEOUT_FLAG="${LOG_FILE}.timedout"
  rm -f "$TIMEOUT_FLAG"

  bash "$DAILY_RUN" > "${LOG_FILE}.out" 2> "${LOG_FILE}.err" &
  RUNNER_PID=$!

  (
    sleep 10800
    if kill -0 "$RUNNER_PID" 2>/dev/null; then
      touch "$TIMEOUT_FLAG"
      # 先温柔杀进程组，再强杀（runner 内部有 python SQL 子进程要一并收掉）
      pkill -TERM -P "$RUNNER_PID" 2>/dev/null
      sleep 2
      kill -9 "$RUNNER_PID" 2>/dev/null
      pkill -9 -P "$RUNNER_PID" 2>/dev/null
    fi
  ) &
  WATCHDOG_PID=$!

  wait "$RUNNER_PID"
  EXIT_CODE=$?
  kill "$WATCHDOG_PID" 2>/dev/null
  wait "$WATCHDOG_PID" 2>/dev/null

  echo "runner exit code: ${EXIT_CODE}"

  # 合并日志
  echo "--- stdout ---"
  cat "${LOG_FILE}.out"
  echo "--- stderr ---"
  cat "${LOG_FILE}.err"

  if [ -f "$TIMEOUT_FLAG" ]; then
    rm -f "$TIMEOUT_FLAG" "$REPORT_PATH"
    echo "FAILED: runner hung (watchdog killed after 3h)"
    "$ALERT_SCRIPT" "runner 挂死 3 小时（watchdog 触发）" "$LOG_FILE"
    exit 1
  fi

  if [ "${EXIT_CODE}" -ne 0 ]; then
    # 失败兜底：runner 可能在写完 JSON 但推送前异常退出，强制删除避免下次误判"已推送"
    rm -f "$REPORT_PATH"
    LAST_ERR=$(tail -n 3 "${LOG_FILE}.err" 2>/dev/null | tr '\n' ' ' | head -c 300)
    echo "FAILED: runner exit code ${EXIT_CODE}"
    "$ALERT_SCRIPT" "runner 执行退出码 ${EXIT_CODE}: ${LAST_ERR}" "$LOG_FILE"
    exit 1
  fi

  echo "SUCCESS: daily report pushed"
  rm -f "${LOG_FILE}.out" "${LOG_FILE}.err"
  exit 0

} 2>&1 | tee -a "$LOG_FILE"
