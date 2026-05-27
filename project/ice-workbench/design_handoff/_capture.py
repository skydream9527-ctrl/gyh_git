"""Screenshot the 4 login states for Claude Design handoff.

Mocks /api/v1/auth/methods + /api/v1/auth/register so all 4 states can
be reached without polluting the database. Run with:

    cd /home/mi/ice-workbench && python3 design_handoff/_capture.py

Output: design_handoff/screenshots/01_login-{A..D}-{desktop,mobile}.png
"""

from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5173"
OUT = Path(__file__).parent / "screenshots"
OUT.mkdir(exist_ok=True)

DESKTOP = {"width": 1280, "height": 800}
MOBILE = {"width": 390, "height": 844}


def state_methods(aegis: bool, password: bool, register: bool):
    return {
        "code": 0,
        "message": "success",
        "data": {
            "aegis_enabled": aegis,
            "password_enabled": password,
            "feishu_oauth_enabled": True,
            "open_register_enabled": register,
        },
    }


CHROMIUM = "/home/mi/.cache/ms-playwright/chromium-1223/chrome-linux64/chrome"


def capture(pw, label: str, viewport: dict, setup):
    """Run a setup callback that puts the page into the target state, then snapshot."""
    browser = pw.chromium.launch(executable_path=CHROMIUM)
    ctx = browser.new_context(viewport=viewport, color_scheme="dark")
    page = ctx.new_page()
    setup(page)
    page.wait_for_timeout(600)  # let animations / fonts settle
    out = OUT / f"01_login-{label}.png"
    page.screenshot(path=str(out), full_page=False)
    print(f"  → {out}")
    browser.close()


def setup_A(page):
    """Aegis warn — aegis_enabled=true, no proxy header so bootstrapMe fails."""
    page.route(
        "**/api/v1/auth/methods",
        lambda r: r.fulfill(json=state_methods(True, True, False)),
    )
    page.route(
        "**/api/v1/auth/me",
        lambda r: r.fulfill(status=401, json={"code": 1, "message": "unauth"}),
    )
    page.goto(f"{BASE}/login")
    # Wait for the warn hint or the retry button to appear
    page.wait_for_selector(".login-hint.warn", timeout=5000)


def setup_B(page):
    """Password login — methods returns password+register both true, default tab."""
    page.route(
        "**/api/v1/auth/methods",
        lambda r: r.fulfill(json=state_methods(False, True, True)),
    )
    page.route(
        "**/api/v1/auth/me",
        lambda r: r.fulfill(status=401, json={"code": 1, "message": "unauth"}),
    )
    page.goto(f"{BASE}/login")
    page.wait_for_selector("input[autocomplete='current-password']", timeout=5000)


def setup_C(page):
    """Register form — same methods but click '去注册'."""
    page.route(
        "**/api/v1/auth/methods",
        lambda r: r.fulfill(json=state_methods(False, True, True)),
    )
    page.route(
        "**/api/v1/auth/me",
        lambda r: r.fulfill(status=401, json={"code": 1, "message": "unauth"}),
    )
    page.goto(f"{BASE}/login")
    page.wait_for_selector("button:has-text('注册')", timeout=5000)
    page.click("button[role='tab']:has-text('注册')")
    page.wait_for_selector("input[autocomplete='new-password']", timeout=5000)


def setup_D(page):
    """Registration pending approval — mock /auth/register success."""
    page.route(
        "**/api/v1/auth/methods",
        lambda r: r.fulfill(json=state_methods(False, True, True)),
    )
    page.route(
        "**/api/v1/auth/me",
        lambda r: r.fulfill(status=401, json={"code": 1, "message": "unauth"}),
    )
    page.route(
        "**/api/v1/auth/register",
        lambda r: r.fulfill(
            json={
                "code": 0,
                "message": "success",
                "data": {
                    "message": "我们已通知管理员审批，通常 1 个工作日内完成。",
                },
            }
        ),
    )
    page.goto(f"{BASE}/login?logout=1")
    page.wait_for_selector("button[role='tab']:has-text('注册')", timeout=5000)
    page.click("button[role='tab']:has-text('注册')")
    page.wait_for_selector("input[autocomplete='new-password']", timeout=5000)
    page.fill("input[autocomplete='username']", "demo.user@example.com")
    page.fill("input[autocomplete='name']", "示例用户")
    pwd = "DesignDemo2026!"
    page.fill("input[autocomplete='new-password']:nth-of-type(1)", pwd)
    # The two password fields share autocomplete=new-password — fill both via locator
    page.locator("input[autocomplete='new-password']").nth(1).fill(pwd)
    page.click("button[type='submit']")
    page.wait_for_selector("text=账号申请已提交", timeout=5000)


def main():
    states = [
        ("A-aegis-warn", setup_A),
        ("B-password-login", setup_B),
        ("C-password-register", setup_C),
        ("D-pending-approval", setup_D),
    ]
    with sync_playwright() as pw:
        for label, fn in states:
            print(f"State {label} desktop")
            capture(pw, f"{label}-desktop", DESKTOP, fn)
            print(f"State {label} mobile")
            capture(pw, f"{label}-mobile", MOBILE, fn)


if __name__ == "__main__":
    main()
