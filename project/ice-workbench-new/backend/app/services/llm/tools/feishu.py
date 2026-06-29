"""Auto-extracted from tool_runner.py — DO NOT edit tool_runner.py for these functions."""
from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from ....core.config import get_settings
from ....core.errors import ErrorCode


async def _feishu_perm_add(
    cli: str, doc_token: str, email: str, perm: str,
    env: dict[str, str] | None = None,
) -> tuple[bool, str]:
    """Run `feishu perm add` for a single email. Returns (ok, message)."""
    proc = await asyncio.create_subprocess_exec(
        cli, "perm", "add", doc_token,
        "--type", "docx",
        "--member-type", "email",
        "--member-id", email,
        "--perm", perm,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )
    try:
        _out_b, err_b = await asyncio.wait_for(proc.communicate(), timeout=20.0)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return False, f"timeout (20s) for {email}"
    err_s = err_b.decode(errors="replace").strip()
    if proc.returncode == 0:
        return True, ""
    return False, (err_s or f"exit {proc.returncode}")[:200]


def _collect_task_xiaomi_emails(task_id: str) -> list[str]:
    """Pull the task owner's + active collaborators' xiaomi_email values.

    Returns deduped lowercase list. Silent on missing fields — users without
    a xiaomi_email simply skip auto-perm and the report stays inaccessible
    to them via this channel (the AccountModal banner nudges them to add it).
    """
    from ....core.storage import read_json as _read_json
    from ....core.storage.paths import get_paths as _gp

    paths = _gp()
    meta = _read_json(paths.task_meta(task_id)) or {}
    collabs = _read_json(paths.task_collaborators(task_id)) or []

    user_ids: list[str] = []
    owner_id = meta.get("owner_id") or meta.get("user_id")
    if owner_id:
        user_ids.append(owner_id)
    for c in collabs:
        if isinstance(c, dict) and c.get("status") == "active" and c.get("user_id"):
            user_ids.append(c["user_id"])

    seen: set[str] = set()
    emails: list[str] = []
    for uid in user_ids:
        if uid in seen:
            continue
        seen.add(uid)
        prof = _read_json(paths.user_profile(uid)) or {}
        xe = (prof.get("xiaomi_email") or "").strip().lower()
        if xe and xe not in emails:
            emails.append(xe)
    return emails


async def _feishu_refresh_user_token(profile: dict) -> dict | None:
    """Refresh an expired Feishu user access token using the stored refresh token.

    On success, updates the user profile with the new tokens and returns a
    token dict suitable for the CLI auth.json format.  Returns None on any
    failure (caller falls back to the global CLI session).
    """
    import json as _json
    import time as _time

    import httpx

    from ....core.config import get_settings as _get_settings
    from ....core.storage import read_json as _read_json
    from ....core.storage import write_json as _write_json
    from ....core.storage.paths import get_paths as _gp

    rt = profile.get("feishu_refresh_token")
    if not rt:
        return None
    rt_exp = profile.get("feishu_refresh_expires_at", 0)
    if _time.time() >= rt_exp - 60:
        return None

    s = _get_settings()
    host = (s.FEISHU_HOST or "https://open.feishu.cn").rstrip("/")
    token_url = f"{host}/open-apis/authen/v1/oidc/refresh_access_token"

    try:
        async with httpx.AsyncClient(timeout=15) as cli:
            app_r = await cli.post(
                f"{host}/open-apis/auth/v3/app_access_token/internal",
                json={"app_id": s.FEISHU_APP_ID, "app_secret": s.FEISHU_APP_SECRET},
            )
            if app_r.status_code >= 400:
                return None
            app_token = app_r.json().get("app_access_token")
            if not app_token:
                return None

            r = await cli.post(
                token_url,
                json={"grant_type": "refresh_token", "refresh_token": rt},
                headers={"Authorization": f"Bearer {app_token}"},
            )
            if r.status_code >= 400:
                return None
            data = r.json().get("data") or {}
            new_at = data.get("access_token")
            if not new_at:
                return None

        now = _time.time()
        new_exp = now + (data.get("expires_in") or 7200)
        new_rt_exp = now + (data.get("refresh_token_expires_in") or 2592000)
        new_rt = data.get("refresh_token", rt)

        uid = profile.get("id")
        if uid:
            paths = _gp()
            prof_path = paths.user_profile(uid)
            current = _read_json(prof_path) or dict(profile)
            current["feishu_access_token"] = new_at
            current["feishu_refresh_token"] = new_rt
            current["feishu_token_expires_at"] = new_exp
            current["feishu_refresh_expires_at"] = new_rt_exp
            _write_json(prof_path, current)

        return {
            "access_token": new_at,
            "refresh_token": new_rt,
            "expires_at": new_exp,
            "refresh_expires_at": new_rt_exp,
            "open_id": profile.get("feishu_user_id", ""),
        }
    except Exception:
        return None


async def _tool_feishu_publish(args: dict, ctx: dict | None = None) -> Any:
    """Create a Feishu doc via the bundled `feishu` CLI.

    When the user has a Feishu OAuth token on file, the doc is created under
    *their* personal space (my_library) so it lands in "我的空间" in the
    Feishu client.  Otherwise falls back to the team wiki space configured
    via FEISHU_DEFAULT_WIKI_SPACE_ID.

    Access provisioning layers (applied in order):
      A. Default location → user's personal space (if UAT available) or team
         wiki space (FEISHU_DEFAULT_WIKI_SPACE_ID).
      B. After create, perm-add the task owner + active collaborators
         (their xiaomi_email) at FEISHU_AUTO_PERM_LEVEL.
      C. Anything in `share_to` gets perm-add at `share_perm` (default edit).

    Per-call args can override the location (wiki_space / wiki_node / folder).
    Perm-add failures are warnings, never fatal — the doc stays usable.
    """
    import json as _json
    import shutil
    import tempfile
    from pathlib import Path

    task_id = (ctx or {}).get("task_id")
    user_id = (ctx or {}).get("user_id")
    title = (args.get("title") or "").strip()
    markdown = args.get("markdown") or ""
    if not title:
        return {"error_code": "VALIDATION_ERROR", "message": "title is required"}
    cli = shutil.which("feishu")
    if not cli:
        return {
            "error_code": "FEISHU_CLI_NOT_INSTALLED",
            "message": "feishu CLI 未安装；请管理员在后端环境安装 feishu 命令行",
        }

    settings = get_settings()

    # --- Determine whether we can act as the user (UAT) ---
    user_feishu_token: dict | None = None
    if user_id:
        from ....core.storage import read_json as _read_json
        from ....core.storage.paths import get_paths as _gp
        _paths = _gp()
        _prof = _read_json(_paths.user_profile(user_id)) or {}
        _at = _prof.get("feishu_access_token")
        _rt = _prof.get("feishu_refresh_token")
        _exp = _prof.get("feishu_token_expires_at", 0)
        import time as _time
        if _at and _time.time() < _exp - 60:
            user_feishu_token = {
                "access_token": _at,
                "refresh_token": _rt or "",
                "expires_at": _exp,
                "refresh_expires_at": _prof.get("feishu_refresh_expires_at", 0),
                "open_id": _prof.get("feishu_user_id", ""),
            }
        elif _rt:
            refreshed = await _feishu_refresh_user_token(_prof)
            if refreshed:
                user_feishu_token = refreshed

    # Resolve location: per-call > user personal > env default.
    wiki_space = (args.get("wiki_space") or "").strip()
    wiki_node = (args.get("wiki_node") or "").strip()
    folder_token = (args.get("folder") or "").strip()
    if not (wiki_space or wiki_node or folder_token):
        if user_feishu_token:
            pass
        else:
            wiki_space = (settings.FEISHU_DEFAULT_WIKI_SPACE_ID or "").strip()
            if not wiki_space:
                folder_token = (settings.FEISHU_DEFAULT_FOLDER_TOKEN or "").strip()

    extra_args: list[str] = []
    if wiki_node:
        extra_args = ["--wiki-node", wiki_node]
    elif wiki_space:
        extra_args = ["--wiki-space", wiki_space]
    elif folder_token:
        extra_args = ["--folder", folder_token]

    # --- Build subprocess environment ---
    sub_env: dict[str, str] | None = None
    tmp_home: str | None = None
    if user_feishu_token:
        tmp_home = tempfile.mkdtemp(prefix="feishu-uat-")
        feishu_dir = Path(tmp_home) / ".feishu"
        feishu_dir.mkdir(parents=True, exist_ok=True)
        token_data = {
            "access_token": user_feishu_token["access_token"],
            "refresh_token": user_feishu_token.get("refresh_token", ""),
            "expires_at": user_feishu_token.get("expires_at", 0),
            "refresh_expires_at": user_feishu_token.get("refresh_expires_at", 0),
            "open_id": user_feishu_token.get("open_id", ""),
        }
        (feishu_dir / "auth.json").write_text(
            _json.dumps(token_data), encoding="utf-8"
        )
        import os as _os
        sub_env = {**_os.environ, "HOME": tmp_home}

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    ) as f:
        f.write(markdown)
        tmp_path = f.name
    try:
        proc = await asyncio.create_subprocess_exec(
            cli, "docx", "create", title, "-f", tmp_path, *extra_args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=sub_env,
        )
        try:
            out_b, err_b = await asyncio.wait_for(proc.communicate(), timeout=90.0)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return {"error_code": "FEISHU_CLI_TIMEOUT", "message": "feishu CLI timeout (90s)"}
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    out_s = out_b.decode(errors="replace")
    err_s = err_b.decode(errors="replace")
    # Reference impl: rc 0/2/3 all carry a usable doc_token; 2/3 = warnings only.
    if proc.returncode not in (0, 2, 3):
        if tmp_home:
            import shutil as _shutil
            _shutil.rmtree(tmp_home, ignore_errors=True)
        return {
            "error_code": "FEISHU_CLI_ERROR",
            "message": (err_s.strip() or f"feishu exit {proc.returncode}")[:600],
        }
    try:
        data = _json.loads(out_s)
    except _json.JSONDecodeError:
        if tmp_home:
            import shutil as _shutil
            _shutil.rmtree(tmp_home, ignore_errors=True)
        return {"raw_output": out_s.strip()[:2000]}

    doc_token = data.get("doc_token", "")
    if user_feishu_token and not (wiki_space or wiki_node or folder_token):
        location = "user_personal"
    else:
        location = (
            f"wiki_space={wiki_space}" if wiki_space
            else f"wiki_node={wiki_node}" if wiki_node
            else f"folder={folder_token}" if folder_token
            else "personal"
        )

    # ----- Auto-permission step (A's tail-end + B + C) -----
    # When using user token, perm-add also needs the user's env so the CLI
    # authenticates as the document owner (personal-space docs are not
    # manageable via the global tenant token).
    perm_env = sub_env
    perm_results: list[dict] = []
    perm_warnings: list[str] = []
    if doc_token:
        task_id = (ctx or {}).get("task_id")
        # B: task owner + active collaborators (deduped)
        auto_level = (settings.FEISHU_AUTO_PERM_LEVEL or "").strip().lower()
        auto_emails: list[str] = []
        if task_id and auto_level in _VALID_PERM_LEVELS:
            try:
                auto_emails = _collect_task_xiaomi_emails(task_id)
            except Exception as exc:
                perm_warnings.append(f"collect collaborators failed: {exc!s}"[:200])

        # C: explicit share_to from the caller
        share_perm_raw = (args.get("share_perm") or "edit").strip().lower()
        share_perm = share_perm_raw if share_perm_raw in _VALID_PERM_LEVELS else "edit"
        share_to_raw = args.get("share_to") or []
        share_to: list[str] = []
        if isinstance(share_to_raw, list):
            for x in share_to_raw:
                if isinstance(x, str):
                    e = x.strip().lower()
                    if e and e not in share_to:
                        share_to.append(e)

        # Run sequentially — perm add is fast (<1s typical) and tiny per
        # team, but parallel would mean N concurrent CLI procs spawning
        # subprocesses on the host; not worth the variance.
        targets: list[tuple[str, str]] = []  # (email, perm)
        for em in auto_emails:
            targets.append((em, auto_level))
        for em in share_to:
            if not any(em == e for e, _ in targets):
                targets.append((em, share_perm))

        for em, p in targets:
            ok, msg = await _feishu_perm_add(cli, doc_token, em, p, env=perm_env)
            perm_results.append({"email": em, "perm": p, "ok": ok, "error": msg or None})
            if not ok:
                perm_warnings.append(f"{em} ({p}): {msg}"[:200])

    # Surface CLI's content-write warnings (e.g. "Whiteboard write failed: 404"
    # when Feishu app lacks PlantUML scope — produces empty 「空白画板」 in the doc).
    # Without this, the agent flies blind and can't retry with PNG charts.
    cli_warnings = data.get("warnings") or []
    if not isinstance(cli_warnings, list):
        cli_warnings = [str(cli_warnings)]

    hint: str | None = None
    if any("Whiteboard write failed" in w for w in cli_warnings):
        hint = (
            "飞书 mermaid 渲染失败（whiteboard PlantUML scope 未开通），文档里 "
            "mermaid block 全部是空白画板。请用 execute_python 出 PNG 图表落到 "
            "files/output/charts/，再调 feishu_upload_image 嵌入；不要在 markdown "
            "里写 ```mermaid``` 块。"
        )

    if tmp_home:
        import shutil as _shutil
        _shutil.rmtree(tmp_home, ignore_errors=True)

    return {
        "url": data.get("url", ""),
        "doc_token": doc_token,
        "title": title,
        "location": location,
        "blocks_added": data.get("blocks_added"),
        "images_processed": data.get("images_processed"),
        "whiteboards_created": data.get("whiteboards_created"),
        "content_warnings": cli_warnings or None,
        "hint": hint,
        "perm_grants": perm_results,
        "perm_warnings": perm_warnings or None,
        "warning": err_s.strip() if proc.returncode in (2, 3) else None,
    }


async def _tool_feishu_send_message(args: dict, ctx: dict | None = None) -> Any:
    import httpx

    from ....core.storage.paths import get_paths

    task_id = (ctx or {}).get("task_id")
    is_daily_report_agent = (ctx or {}).get("agent_id") == "djy-daily-report"
    title = (args.get("title") or "").strip()
    content = (args.get("content") or "").strip()
    if not title or not content:
        return {"error_code": "VALIDATION_ERROR", "message": "title and content are required"}

    settings = get_settings()
    receive_id = (args.get("receive_id") or settings.FEISHU_DEFAULT_RECEIVE_ID or "").strip()
    receive_id_type = (
        args.get("receive_id_type") or settings.FEISHU_DEFAULT_RECEIVE_ID_TYPE or "chat_id"
    ).strip()
    webhook_url = (args.get("webhook_url") or "").strip()
    sign_secret = (args.get("sign_secret") or "").strip()
    image_path = (args.get("image_path") or "").strip()
    html_url = (args.get("html_url") or "").strip()
    template = (args.get("template") or "blue").strip()
    if template not in {"blue", "green", "red", "yellow", "grey", "purple"}:
        template = "blue"

    duplicate_cache_path = None
    duplicate_sig = ""
    if is_daily_report_agent and webhook_url:
        if not image_path or not html_url:
            return {
                "error_code": "DAILY_REPORT_FORMAT_REQUIRED",
                "message": (
                    "日报推送到飞书群必须使用 HTML 截图 + HTML 链接："
                    "请先生成 daily_report_preview.html 和 daily_report_preview.png，"
                    "再传 image_path='daily_report_preview.png' 与 html_url；"
                    "禁止直接推送整份 Markdown。"
                ),
            }
        table_lines = sum(1 for line in content.splitlines() if line.strip().startswith("|"))
        heading_lines = sum(1 for line in content.splitlines() if line.lstrip().startswith("#"))
        if len(content) > 1200 or table_lines >= 3 or heading_lines >= 2:
            return {
                "error_code": "DAILY_REPORT_SUMMARY_TOO_LONG",
                "message": (
                    "日报飞书消息正文只能放 3-6 行摘要，完整内容请放在 HTML 截图和 HTML 链接中；"
                    "不要把整份 Markdown 表格作为 content 发送。"
                ),
            }
        if task_id:
            dedupe_payload = {
                "title": title,
                "content": content,
                "webhook_url": webhook_url,
                "image_path": image_path,
                "html_url": html_url,
            }
            duplicate_sig = hashlib.sha256(
                json.dumps(dedupe_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
            ).hexdigest()
            duplicate_cache_path = get_paths().task_dir(task_id) / ".feishu_send_dedupe.json"
            try:
                duplicate_cache = json.loads(duplicate_cache_path.read_text(encoding="utf-8"))
            except Exception:
                duplicate_cache = {}
            if (
                duplicate_cache.get("signature") == duplicate_sig
                and time.time() - float(duplicate_cache.get("sent_at", 0)) < 120
            ):
                return {
                    "sent": False,
                    "duplicate_suppressed": True,
                    "message": "检测到 120 秒内完全相同的日报飞书消息，已阻止重复发送。",
                    "html_url": html_url or None,
                }

    host = (settings.FEISHU_HOST or "https://open.feishu.cn").rstrip("/")
    image_key = ""
    if image_path:
        if not task_id:
            return {"error_code": "VALIDATION_ERROR", "message": "image_path needs a task context"}
        paths = get_paths()
        out_root = paths.task_files_output(task_id).resolve()
        candidate = (out_root / image_path).resolve()
        try:
            candidate.relative_to(out_root)
        except ValueError:
            return {
                "error_code": "PATH_OUTSIDE_TASK_WORKSPACE",
                "message": f"image_path must be under {out_root}",
            }
        if not candidate.is_file():
            return {"error_code": "FILE_NOT_FOUND", "message": f"image not found: {image_path}"}
        if candidate.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
            return {"error_code": "VALIDATION_ERROR", "message": "image_path must be PNG/JPG"}
        if candidate.stat().st_size > 10 * 1024 * 1024:
            return {"error_code": "IMAGE_TOO_LARGE", "message": f"image > 10MB: {image_path}"}
        if not settings.FEISHU_APP_ID or not settings.FEISHU_APP_SECRET:
            return {
                "error_code": "FEISHU_APP_CREDENTIAL_REQUIRED",
                "message": "发送图片需要 FEISHU_APP_ID / FEISHU_APP_SECRET 用于上传消息图片",
            }
        async with httpx.AsyncClient(timeout=30) as cli:
            token_resp = await cli.post(
                f"{host}/open-apis/auth/v3/tenant_access_token/internal",
                json={"app_id": settings.FEISHU_APP_ID, "app_secret": settings.FEISHU_APP_SECRET},
            )
            try:
                token_data = token_resp.json()
            except Exception:
                token_data = {"raw": token_resp.text[:300]}
            if token_resp.status_code >= 400 or token_data.get("code") not in (0, "0", None):
                return {
                    "error_code": "FEISHU_TOKEN_FAILED",
                    "message": str(token_data)[:800],
                }
            token = token_data.get("tenant_access_token")
            if not token:
                return {"error_code": "FEISHU_TOKEN_FAILED", "message": "tenant_access_token is empty"}
            mime = "image/png" if candidate.suffix.lower() == ".png" else "image/jpeg"
            with candidate.open("rb") as fh:
                img_resp = await cli.post(
                    f"{host}/open-apis/im/v1/images",
                    headers={"Authorization": f"Bearer {token}"},
                    data={"image_type": "message"},
                    files={"image": (candidate.name, fh, mime)},
                )
            try:
                img_data = img_resp.json()
            except Exception:
                img_data = {"raw": img_resp.text[:300]}
            if img_resp.status_code >= 400 or img_data.get("code") not in (0, "0", None):
                return {
                    "error_code": "FEISHU_IMAGE_UPLOAD_FAILED",
                    "message": str(img_data)[:800],
                }
            image_key = ((img_data.get("data") or {}).get("image_key") or "").strip()
            if not image_key:
                return {"error_code": "FEISHU_IMAGE_UPLOAD_FAILED", "message": "image_key is empty"}

    elements: list[dict[str, Any]] = []
    if image_key:
        elements.append({
            "tag": "img",
            "img_key": image_key,
            "alt": {"tag": "plain_text", "content": title},
        })
    card_content = content
    if html_url:
        card_content = f"{card_content}\n\n[打开 HTML 报告]({html_url})"
    elements.append({
        "tag": "div",
        "text": {"tag": "lark_md", "content": card_content},
    })

    card = {
        "header": {
            "title": {"tag": "plain_text", "content": title},
            "template": template,
        },
        "elements": elements,
    }

    if webhook_url:
        parsed = urlparse(webhook_url)
        allowed_hosts = {"open.feishu.cn"}
        configured_host = urlparse(settings.FEISHU_HOST or "").netloc
        if configured_host:
            allowed_hosts.add(configured_host)
        if (
            parsed.scheme != "https"
            or parsed.netloc not in allowed_hosts
            or not parsed.path.startswith("/open-apis/bot/v2/hook/")
        ):
            return {
                "error_code": "FEISHU_WEBHOOK_INVALID",
                "message": "飞书机器人 Webhook 必须是 https://open.feishu.cn/open-apis/bot/v2/hook/... 格式",
            }
        payload: dict[str, Any] = {
            "msg_type": "interactive",
            "card": card,
        }
        if sign_secret:
            timestamp = str(int(time.time()))
            string_to_sign = f"{timestamp}\n{sign_secret}"
            sign = base64.b64encode(
                hmac.new(string_to_sign.encode("utf-8"), b"", digestmod=hashlib.sha256).digest()
            ).decode("utf-8")
            payload["timestamp"] = timestamp
            payload["sign"] = sign
        async with httpx.AsyncClient(timeout=15) as cli:
            resp = await cli.post(webhook_url, json=payload)
        if resp.status_code >= 400:
            return {
                "error_code": "FEISHU_WEBHOOK_HTTP_ERROR",
                "message": resp.text[:800],
            }
        try:
            data = resp.json()
        except Exception:
            data = {"raw": resp.text[:800]}
        code = data.get("code") or data.get("StatusCode")
        if code not in ("0", 0, None):
            return {
                "error_code": "FEISHU_WEBHOOK_FAILED",
                "message": str(data)[:800],
            }
        if duplicate_cache_path and duplicate_sig:
            try:
                duplicate_cache_path.write_text(
                    json.dumps(
                        {"signature": duplicate_sig, "sent_at": time.time()},
                        ensure_ascii=False,
                    ),
                    encoding="utf-8",
                )
            except Exception:
                pass
        return {
            "sent": True,
            "delivery": "webhook",
            "webhook": parsed.path.rsplit("/", 1)[-1][:8] + "***",
            "image_embedded": bool(image_key),
            "html_url": html_url or None,
            "raw": data,
        }

    if (ctx or {}).get("agent_id") == "djy-daily-report":
        return {
            "error_code": "FEISHU_WEBHOOK_REQUIRED",
            "message": (
                "日报推送必须使用用户提供的飞书机器人 Webhook 地址；"
                "请传 webhook_url，可选传 sign_secret。"
            ),
        }

    if not settings.FEISHU_APP_ID or not settings.FEISHU_APP_SECRET:
        return {
            "error_code": "FEISHU_NOT_CONFIGURED",
            "message": "缺少 FEISHU_APP_ID / FEISHU_APP_SECRET，无法发送飞书消息",
        }

    if not receive_id:
        return {
            "error_code": "FEISHU_RECEIVE_ID_MISSING",
            "message": "缺少飞书消息接收目标：请传 receive_id 或配置 FEISHU_DEFAULT_RECEIVE_ID",
        }
    if receive_id_type not in {"chat_id", "open_id", "user_id", "union_id", "email"}:
        return {"error_code": "VALIDATION_ERROR", "message": f"invalid receive_id_type: {receive_id_type}"}

    async with httpx.AsyncClient(timeout=15) as cli:
        token_resp = await cli.post(
            f"{host}/open-apis/auth/v3/tenant_access_token/internal",
            json={"app_id": settings.FEISHU_APP_ID, "app_secret": settings.FEISHU_APP_SECRET},
        )
        if token_resp.status_code >= 400:
            return {
                "error_code": "FEISHU_TOKEN_HTTP_ERROR",
                "message": token_resp.text[:500],
            }
        token_data = token_resp.json()
        if token_data.get("code") != 0:
            return {
                "error_code": "FEISHU_TOKEN_FAILED",
                "message": str(token_data)[:500],
            }
        token = token_data.get("tenant_access_token")
        if not token:
            return {"error_code": "FEISHU_TOKEN_FAILED", "message": "tenant_access_token is empty"}

        msg_resp = await cli.post(
            f"{host}/open-apis/im/v1/messages",
            params={"receive_id_type": receive_id_type},
            headers={"Authorization": f"Bearer {token}"},
            json={
                "receive_id": receive_id,
                "msg_type": "interactive",
                "content": json.dumps(card, ensure_ascii=False),
            },
        )
    if msg_resp.status_code >= 400:
        return {
            "error_code": "FEISHU_MESSAGE_HTTP_ERROR",
            "message": msg_resp.text[:800],
            "receive_id_type": receive_id_type,
        }
    data = msg_resp.json()
    if data.get("code") != 0:
        return {
            "error_code": "FEISHU_MESSAGE_FAILED",
            "message": str(data)[:800],
            "receive_id_type": receive_id_type,
        }
    return {
        "sent": True,
        "delivery": "app_im",
        "receive_id_type": receive_id_type,
        "receive_id": receive_id,
        "message_id": (data.get("data") or {}).get("message_id"),
        "image_embedded": bool(image_key),
        "html_url": html_url or None,
        "raw": data,
    }


async def _tool_feishu_upload_image(args: dict, ctx: dict | None = None) -> Any:
    """Upload a PNG/JPG from the task workspace to a Feishu doc.

    Wraps `feishu docx upload-image <doc_token> --file <path>`.
    Path must resolve under <task_workspace>/files/output/ — absolute escapes
    are rejected. Returns image_token (used for embedding) + raw stdout.
    """
    import json as _json
    import shutil

    from ....core.storage.paths import get_paths

    doc_token = (args.get("doc_token") or "").strip()
    rel = (args.get("image_path") or "").strip()
    if not doc_token or not rel:
        return {"error_code": "VALIDATION_ERROR", "message": "doc_token and image_path are required"}
    task_id = (ctx or {}).get("task_id")
    if not task_id:
        return {"error_code": "VALIDATION_ERROR", "message": "feishu_upload_image needs a task context"}

    cli = shutil.which("feishu")
    if not cli:
        return {
            "error_code": "FEISHU_CLI_NOT_INSTALLED",
            "message": "feishu CLI 未安装；请管理员在后端环境安装 feishu 命令行",
        }

    # Resolve image_path against task output dir; reject escapes.
    paths = get_paths()
    out_root = paths.task_files_output(task_id).resolve()
    candidate = (out_root / rel).resolve()
    try:
        candidate.relative_to(out_root)
    except ValueError:
        return {
            "error_code": "PATH_OUTSIDE_TASK_WORKSPACE",
            "message": f"image_path must be under {out_root}",
        }
    if not candidate.is_file():
        return {
            "error_code": "FILE_NOT_FOUND",
            "message": f"image not found: {rel}",
        }
    if candidate.stat().st_size > 10 * 1024 * 1024:
        return {
            "error_code": "IMAGE_TOO_LARGE",
            "message": f"image > 10MB: {rel}",
        }

    proc = await asyncio.create_subprocess_exec(
        cli, "docx", "upload-image", doc_token, "--file", str(candidate),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        out_b, err_b = await asyncio.wait_for(proc.communicate(), timeout=60.0)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return {"error_code": "FEISHU_CLI_TIMEOUT", "message": "feishu upload-image timeout (60s)"}

    out_s = out_b.decode(errors="replace")
    err_s = err_b.decode(errors="replace")
    if proc.returncode != 0:
        return {
            "error_code": "FEISHU_CLI_ERROR",
            "message": (err_s.strip() or f"feishu exit {proc.returncode}")[:600],
        }
    try:
        data = _json.loads(out_s)
    except _json.JSONDecodeError:
        # CLI may print plain token; normalize
        token = out_s.strip().split()[-1] if out_s.strip() else ""
        return {"image_token": token, "raw_output": out_s.strip()[:600]}
    return {
        "image_token": data.get("image_token") or data.get("token") or "",
        "doc_token": doc_token,
        "image_path": rel,
        "raw": data,
    }


