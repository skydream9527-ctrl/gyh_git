#!/usr/bin/env python3
"""飞书图床上传 · 上传本地 PNG/JPG，返回 image_key

用法：
  python3 feishu_upload_image.py <image_path>   # 输出 image_key 到 stdout

凭证：
  从 skill 根目录 .env 自动加载 FEISHU_APP_ID / FEISHU_APP_SECRET
"""
import json
import os
import pathlib
import sys
import urllib.request


def _read_env(path: pathlib.Path, override: bool = False):
    if not path.exists():
        return
    for ln in path.read_text().splitlines():
        line = ln.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        key = k.strip()
        val = v.strip().strip("'\"")
        if override:
            os.environ[key] = val
        else:
            os.environ.setdefault(key, val)


def load_env():
    skill_root = pathlib.Path(__file__).resolve().parent.parent.parent
    project_root = skill_root.parent.parent
    _read_env(skill_root / ".env")
    _read_env(project_root / ".env", override=True)


def get_tenant_token(app_id: str, app_secret: str) -> str:
    req = urllib.request.Request(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        data=json.dumps({"app_id": app_id, "app_secret": app_secret}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        result = json.loads(r.read().decode())
    if result.get("code") != 0:
        raise RuntimeError(f"tenant_access_token 获取失败: {result}")
    return result["tenant_access_token"]


def upload_image(token: str, image_path: str) -> str:
    """上传图片到飞书图床，返回 image_key"""
    import mimetypes
    import uuid

    boundary = uuid.uuid4().hex
    mime, _ = mimetypes.guess_type(image_path)
    mime = mime or "image/png"
    filename = os.path.basename(image_path)

    with open(image_path, "rb") as f:
        file_content = f.read()

    parts = []
    parts.append(f"--{boundary}\r\n".encode())
    parts.append(b'Content-Disposition: form-data; name="image_type"\r\n\r\n')
    parts.append(b"message\r\n")
    parts.append(f"--{boundary}\r\n".encode())
    parts.append(
        f'Content-Disposition: form-data; name="image"; filename="{filename}"\r\n'.encode()
    )
    parts.append(f"Content-Type: {mime}\r\n\r\n".encode())
    parts.append(file_content)
    parts.append(b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    body = b"".join(parts)

    req = urllib.request.Request(
        "https://open.feishu.cn/open-apis/im/v1/images",
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        result = json.loads(r.read().decode())
    if result.get("code") != 0:
        raise RuntimeError(f"图片上传失败: {result}")
    return result["data"]["image_key"]


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)

    load_env()
    try:
        app_id = os.environ["FEISHU_APP_ID"]
        app_secret = os.environ["FEISHU_APP_SECRET"]
    except KeyError as e:
        print(f"ERROR: .env 缺少 {e}", file=sys.stderr)
        sys.exit(2)

    token = get_tenant_token(app_id, app_secret)
    key = upload_image(token, sys.argv[1])
    print(key)


if __name__ == "__main__":
    main()
