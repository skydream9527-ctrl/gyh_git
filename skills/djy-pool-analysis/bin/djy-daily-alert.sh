#!/bin/bash
# 纯 bash 失败告警（不依赖 Claude）
# 用法：djy-daily-alert.sh "<失败原因>" <日志文件路径>

REASON="${1:-未知错误}"
LOG_PATH="${2:-}"
TS=$(date "+%Y-%m-%d %H:%M")

TITLE_PLAIN="❌ djy 内容池日报跑数失败 · ${TS}"
BODY_MD="**❌ 日报跑数失败**\n时间：${TS}\n原因：<font color='red'>${REASON}</font>\n日志：\`${LOG_PATH}\`\n请在 Claude Code 里手动重跑。"

cat > /tmp/djy_daily_alert.json <<EOF
{
  "card": {
    "header": {
      "title": {"tag": "plain_text", "content": "${TITLE_PLAIN}"},
      "template": "red"
    },
    "elements": [
      {"tag": "div", "text": {"tag": "lark_md", "content": "${BODY_MD}"}}
    ]
  }
}
EOF

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

python3 \
  "$SKILL_ROOT/scripts/shared/feishu_post.py" \
  /tmp/djy_daily_alert.json
