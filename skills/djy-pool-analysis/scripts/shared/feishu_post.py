#!/usr/bin/env python3
"""飞书消息推送（webhook 或开放平台机器人 + 自动识别 post/interactive）。

用法：
  python3 feishu_post.py <json_file>   # 从文件读
  python3 feishu_post.py -              # 从 stdin 读

凭证：
  从 skill 根目录 `.env` 自动加载 FEISHU_WEBHOOK / FEISHU_SECRET
  从项目根 `.env` 自动加载 FEISHU_APP_ID / FEISHU_APP_SECRET
  命令行 env var 可覆盖（便于临时测试）
  优先用 webhook；如果没有 webhook，则使用 FEISHU_APP_ID / FEISHU_APP_SECRET
  + FEISHU_RECEIVE_ID 通过开放平台 IM API 发送。FEISHU_RECEIVE_ID_TYPE 默认为 chat_id。

支持的 JSON 格式（通过字段自动识别）：

格式 1 · post（纯文本简单版）：
{
  "title": "📊 ...",
  "lines": ["第一段", "第二段", ...]
}

格式 2 · interactive（交互卡片推荐版，日报默认）：
{
  "card": { ... 原生飞书卡片结构 ... }
}
  - header: 头部 {title / subtitle / template: blue/red/green/yellow/grey/purple}
  - elements: 卡片体元素列表
    · {"tag":"markdown","content":"**加粗** `code` <font color='red'>红</font>"}
    · {"tag":"div","text":{"tag":"lark_md","content":"..."}}
    · {"tag":"hr"}  分隔线
    · {"tag":"note","elements":[{"tag":"plain_text","content":"脚注"}]}
    · {"tag":"column_set","columns":[{"tag":"column",...}, ...]}  多列布局

飞书坑位备注：
- post 不支持空段落 / style 数组 → 脚本自动过滤空行
- lark_md 支持 **粗体** / `code` / <font color='red'>红</font> / [link](url)
- plain_text 不支持任何 markdown
"""
import base64
import hashlib
import hmac
import json
import os
import pathlib
import sys
import time
import urllib.request


def _read_env(path: pathlib.Path, override: bool = False):
    if not path.exists():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        name = key.strip()
        value = val.strip().strip("'").strip('"')
        if override:
            os.environ[name] = value
        else:
            os.environ.setdefault(name, value)


def load_env_file():
    skill_root = pathlib.Path(__file__).resolve().parent.parent.parent
    project_root = skill_root.parent.parent
    _read_env(skill_root / ".env")
    _read_env(project_root / ".env", override=True)


def gen_sign(timestamp: int, secret: str) -> str:
    s = f"{timestamp}\n{secret}"
    return base64.b64encode(hmac.new(s.encode(), digestmod=hashlib.sha256).digest()).decode()


def build_post_content(data: dict) -> dict:
    lines = [ln for ln in data["lines"] if ln.strip()]
    paragraphs = [[{"tag": "text", "text": ln}] for ln in lines]
    return {"post": {"zh_cn": {"title": data["title"], "content": paragraphs}}}


def build_message(data: dict) -> tuple[str, dict]:
    if "card" in data:
        return "interactive", data["card"]
    elif "lines" in data and "title" in data:
        return "post", build_post_content(data)
    else:
        raise ValueError("JSON 必须包含 `card`（interactive）或 `title`+`lines`（post）")


def send_webhook(webhook: str, secret: str, data: dict) -> dict:
    msg_type, content = build_message(data)
    if msg_type == "interactive":
        payload = {"msg_type": msg_type, "card": content}
    else:
        payload = {"msg_type": msg_type, "content": content}

    ts = int(time.time())
    payload["timestamp"] = str(ts)
    payload["sign"] = gen_sign(ts, secret)

    req = urllib.request.Request(
        webhook,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_tenant_token(app_id: str, app_secret: str) -> str:
    req = urllib.request.Request(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        data=json.dumps({"app_id": app_id, "app_secret": app_secret}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    if result.get("code") != 0:
        raise RuntimeError(f"tenant_access_token 获取失败: {result}")
    return result["tenant_access_token"]


def send_im(app_id: str, app_secret: str, receive_id: str, receive_id_type: str, data: dict) -> dict:
    token = get_tenant_token(app_id, app_secret)
    msg_type, content = build_message(data)
    req = urllib.request.Request(
        f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type={receive_id_type}",
        data=json.dumps(
            {
                "receive_id": receive_id,
                "msg_type": msg_type,
                "content": json.dumps(content, ensure_ascii=False),
            },
            ensure_ascii=False,
        ).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)

    load_env_file()
    path = sys.argv[1]
    raw = sys.stdin.read() if path == "-" else open(path).read()
    data = json.loads(raw)

    webhook = os.environ.get("FEISHU_WEBHOOK")
    webhook_secret = os.environ.get("FEISHU_SECRET")
    app_id = os.environ.get("FEISHU_APP_ID")
    app_secret = os.environ.get("FEISHU_APP_SECRET")
    receive_id = os.environ.get("FEISHU_RECEIVE_ID")
    receive_id_type = os.environ.get("FEISHU_RECEIVE_ID_TYPE", "chat_id")

    if webhook and webhook_secret:
        result = send_webhook(webhook, webhook_secret, data)
    elif app_id and app_secret and receive_id:
        result = send_im(app_id, app_secret, receive_id, receive_id_type, data)
    else:
        print(
            "ERROR: 缺少飞书推送配置。请配置 FEISHU_WEBHOOK + FEISHU_SECRET，"
            "或配置 FEISHU_APP_ID + FEISHU_APP_SECRET + FEISHU_RECEIVE_ID。",
            file=sys.stderr,
        )
        sys.exit(2)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result.get("code") not in (0, None) and result.get("StatusCode") not in (0, None):
        sys.exit(1)


if __name__ == "__main__":
    main()
