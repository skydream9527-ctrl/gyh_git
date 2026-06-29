#!/bin/bash
# 提交+推送当日产出到 GitLab，触发 Pages 刷新
# 用法: git_push_daily.sh [YYYYMMDD]
set -euo pipefail

REPO_DIR="${DJY_OUTPUT_ROOT:-$HOME/Desktop/ai_djy_pool_analysis}"
DATE="${1:-$(date +%Y%m%d)}"

cd "$REPO_DIR"

# 同步 remote：daily-run.sh Step 7 push HTML 之后到这里，远端可能又有新 commit 落地
git fetch origin main 2>&1 | tail -3
git rebase origin/main 2>&1 | tail -10

git add reports/ daily_reports/ dirty/ 2>/dev/null || true

if git diff --cached --quiet; then
    echo "nothing to commit"
    exit 0
fi

git commit -m "daily: ${DATE} report artifacts"
git push origin main

echo "pushed daily artifacts for ${DATE}"
