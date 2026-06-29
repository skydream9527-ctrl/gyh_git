#!/usr/bin/env python3
"""HTML → 整页长图 PNG（日报飞书推送用，2026-05-11 起替代 7 张分图方案）

用法:
  python3 chart_html_to_longpng.py <html_path> <out_png> [--width 1500]

依赖:
  - Playwright (pip install playwright)
  - macOS：本机 Chrome（channel='chrome'，免去装 chromium）
  - Linux：playwright bundled chromium（playwright install chromium）
"""
import os
import shutil
import sys
from pathlib import Path

# Linux：playwright bundled chromium 在仓库本地 .playwright-browsers/，与 ~/.cache 默认路径不一致。
# macOS：走系统 Chrome，不需要此 env。
if sys.platform != "darwin":
    _DEFAULT_BROWSERS = os.path.expanduser("~/djy-deploy/.playwright-browsers")
    if os.path.isdir(_DEFAULT_BROWSERS):
        os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", _DEFAULT_BROWSERS)

from playwright.sync_api import sync_playwright  # noqa: E402


def shoot_longpng(html_path: str, out_png: str, width: int = 1500) -> None:
    # 2026-05-15: 改为 set_content 直接喂 HTML 字符串，不再走 file:// 协议。
    # 起因：cron 启动的 chromium 子进程访问 ~/Desktop 被 macOS TCC 拒
    # （ERR_ACCESS_DENIED）。Python 进程本身能读文件，由 Python 把 HTML 内容
    # 灌给 Chrome；Chrome 只负责渲染字符串，不触碰文件系统，绕开 TCC。
    # 前提：HTML 自包含（CSS inline、外部资源全走 https CDN，无本地相对路径），
    # 当前 chart_gen_html.py 产出的 HTML 满足该约束。
    html_content = Path(html_path).read_text(encoding="utf-8")
    out_abs = str(Path(out_png).resolve())
    Path(out_png).parent.mkdir(parents=True, exist_ok=True)

    # macOS / Linux 优先用系统 Chrome（避免 bundled Chromium 在受限环境里
    # sandbox_host_linux.cc SIGTRAP），找不到系统 Chrome 时再走 Playwright bundled Chromium。
    launch_kwargs = {"headless": True}
    if sys.platform == "darwin" or shutil.which("google-chrome"):
        launch_kwargs["channel"] = "chrome"
    elif sys.platform != "darwin":
        launch_kwargs["args"] = [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--no-zygote",
            "--disable-dev-shm-usage",
        ]

    with sync_playwright() as p:
        browser = p.chromium.launch(**launch_kwargs)
        ctx = browser.new_context(
            viewport={"width": width, "height": 1000},
            device_scale_factor=2,
        )
        page = ctx.new_page()
        page.set_content(html_content, wait_until="networkidle", timeout=60_000)
        page.wait_for_timeout(1200)
        page.screenshot(path=out_abs, full_page=True, type="png")
        browser.close()


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0 if args else 1)

    html_path = args[0]
    out_png = args[1]
    width = 1500
    if "--width" in args:
        width = int(args[args.index("--width") + 1])

    shoot_longpng(html_path, out_png, width)
    print(f"OK: {out_png}")


if __name__ == "__main__":
    main()
