import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuthStore } from "@/stores/authStore";
import { authApi, sysApi } from "@/api/endpoints";
import type { GlobalToggles } from "@/types/api";
import { useUIStore } from "@/stores/uiStore";
import { checkLoginLimit, clearLoginLimit, recordLoginFailure } from "@/utils/loginRateLimit";
import "./Login.css";

/**
 * 两种登录方式（后端 /auth/methods 控制可见性）：
 *  ① 米盾代理：浏览器 cookie 由代理注入，进入页面自动 bootstrapMe。
 *  ② 账号密码：POST /auth/login 换 JWT。
 */

type Tab = "aegis" | "password";

/**
 * Password rule checklist — must mirror the backend's `_validate_password_strength`
 * in `backend/app/services/auth_svc.py`. Showing the rules inline both
 * reduces user frustration (no submit-then-error) and surfaces what the
 * server actually enforces, so people can't silently set weaker policies
 * by editing the placeholder.
 */
const BANNED_BASES = [
  "password", "passw0rd", "password1", "password123",
  "admin", "admin123", "admin1234", "administrator",
  "qwerty", "qwerty123", "qwertyuiop",
  "12345678", "123456789", "1234567890", "11111111", "00000000",
  "letmein", "welcome", "iloveyou", "abc12345", "testtest",
  "test123", "test1234",
  "iceworkbench", "ice123",
];
const LEET: Record<string, string> = {
  "@": "a", "0": "o", "1": "i", "3": "e", "$": "s", "!": "i", "5": "s", "7": "t",
};
function canonicalize(s: string): string {
  return s.toLowerCase().split("").map((c) => LEET[c] ?? c).join("");
}
function hasOverlap(haystack: string, needle: string, minLen = 4): boolean {
  if (!needle || needle.length < minLen) return false;
  const h = haystack.toLowerCase();
  const n = needle.toLowerCase();
  if (n.length <= minLen) return h.includes(n);
  for (let i = 0; i <= n.length - minLen; i++) {
    if (h.includes(n.slice(i, i + minLen))) return true;
  }
  return false;
}

function PasswordRuleList({
  password,
  email,
  name,
}: {
  password: string;
  email: string;
  name: string;
}) {
  // Each rule returns "ok" / "fail" / "idle" (idle = empty pwd, no judgment yet).
  const idle = password.length === 0;
  const lenOk = password.length >= 10 && password.length <= 128;
  const classes =
    Number(/[a-z]/.test(password)) +
    Number(/[A-Z]/.test(password)) +
    Number(/[0-9]/.test(password)) +
    Number(/[^A-Za-z0-9]/.test(password));
  const classesOk = classes >= 3;
  const noRepeat = !/(.)\1{3,}/.test(password);
  // 4+ ascending: check codepoint diff = -1 step three times in a row
  let noSeq = true;
  const lower = password.toLowerCase();
  for (let i = 0; i < lower.length - 3; i++) {
    const d1 = lower.charCodeAt(i + 1) - lower.charCodeAt(i);
    const d2 = lower.charCodeAt(i + 2) - lower.charCodeAt(i + 1);
    const d3 = lower.charCodeAt(i + 3) - lower.charCodeAt(i + 2);
    if (d1 === 1 && d2 === 1 && d3 === 1) {
      noSeq = false;
      break;
    }
  }
  const canon = canonicalize(password);
  const canonAlpha = canon.replace(/[^a-z0-9]/g, "");
  const noBanned = !BANNED_BASES.some((b) => canonAlpha.includes(b));
  const localPart = email.split("@")[0] ?? "";
  const noOverlap =
    !hasOverlap(canon, localPart) && !hasOverlap(canon, name);

  const rules: { ok: boolean; label: string }[] = [
    { ok: lenOk, label: "长度 10–128 位" },
    { ok: classesOk, label: "至少含 3 类字符（大写 / 小写 / 数字 / 符号）" },
    { ok: noBanned, label: "不能是常见弱口令（如 password / admin / qwerty / 123456 及其 l33t 变体）" },
    { ok: noRepeat, label: "不能有 4 个以上重复字符（如 aaaa / 1111）" },
    { ok: noSeq, label: "不能有 4 个以上连续递增字符（如 1234 / abcd）" },
    { ok: noOverlap, label: "不能包含账号 / 姓名连续 4 字符以上的片段" },
  ];

  return (
    <ul className="password-rules">
      {rules.map((r) => {
        const status = idle ? "idle" : r.ok ? "ok" : "fail";
        return (
          <li key={r.label} data-status={status}>
            <span className="pr-mark" aria-hidden>
              {idle ? "○" : r.ok ? "✓" : "✗"}
            </span>
            <span>{r.label}</span>
          </li>
        );
      })}
    </ul>
  );
}

export function LoginPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const justLoggedOut = searchParams.get("logout") === "1";

  const bootstrapMe = useAuthStore((s) => s.bootstrapMe);
  const login = useAuthStore((s) => s.login);
  const register = useAuthStore((s) => s.register);
  const logoutStore = useAuthStore((s) => s.logout);
  const user = useAuthStore((s) => s.user);
  const pushToast = useUIStore((s) => s.pushToast);

  const [methods, setMethods] = useState<{
    aegis_enabled: boolean;
    password_enabled: boolean;
    open_register_enabled: boolean;
  } | null>(null);
  const [tab, setTab] = useState<Tab>("aegis");
  const [pwMode, setPwMode] = useState<"login" | "register">("login");
  const [checking, setChecking] = useState(!justLoggedOut);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({ email: "", password: "" });
  const [regForm, setRegForm] = useState({
    email: "",
    name: "",
    password: "",
    confirm: "",
    xiaomi_email: "",
  });
  const [submittedForApproval, setSubmittedForApproval] = useState<{
    email: string;
    name: string;
    message: string;
  } | null>(null);
  const [toggles, setToggles] = useState<GlobalToggles | null>(null);

  // 读取后端启用了哪些登录方式
  useEffect(() => {
    authApi
      .methods()
      .then((m) => {
        setMethods({
          aegis_enabled: m.aegis_enabled,
          password_enabled: m.password_enabled,
          open_register_enabled: m.open_register_enabled,
        });
        // 若米盾已启用且不是刚登出，保持 aegis tab；否则默认密码
        if (!m.aegis_enabled && m.password_enabled) setTab("password");
      })
      .catch(() => {
        // Conservative fallback when /auth/methods is unreachable: only
        // password login, registration disabled. Matches backend default.
        setMethods({ aegis_enabled: false, password_enabled: true, open_register_enabled: false });
        setTab("password");
      });
    sysApi.toggles().then(setToggles).catch(() => {});
  }, []);

  // `?logout=1` 明确要求登出：真的清掉 token + store 里的 user，
  // 否则后续密码登录失败时 useEffect 会看到旧 user 把人放进 /dashboard。
  useEffect(() => {
    if (justLoggedOut) {
      logoutStore();
    }
  }, [justLoggedOut, logoutStore]);

  // 米盾模式自动验证身份
  useEffect(() => {
    if (justLoggedOut) {
      setChecking(false);
      return;
    }
    let cancelled = false;
    bootstrapMe().finally(() => {
      if (!cancelled) setChecking(false);
    });
    return () => {
      cancelled = true;
    };
  }, [bootstrapMe, justLoggedOut]);

  // 登录成功 → 进 Dashboard
  // 但当用户刚提交完注册申请（submittedForApproval 非空）时，必须停留在审批页。
  // 否则在本地 dev_bypass 启用时，bootstrapMe 会把请求识别成 admin，user 立刻
  // 被设置 → 跳到 dashboard，导致看不到"待审批"提示。
  useEffect(() => {
    if (user && !justLoggedOut && !submittedForApproval) {
      navigate("/dashboard", { replace: true });
    }
  }, [user, navigate, justLoggedOut, submittedForApproval]);

  const clearLogoutFlag = () => {
    if (justLoggedOut) {
      searchParams.delete("logout");
      setSearchParams(searchParams, { replace: true });
    }
  };

  const retryAegis = () => {
    clearLogoutFlag();
    setChecking(true);
    bootstrapMe().finally(() => setChecking(false));
  };

  const submitPassword = async (email: string, password: string) => {
    if (!email.trim() || !password) {
      pushToast("warning", "请输入账号和密码");
      return;
    }
    // 客户端 5 分钟内 5 次失败软锁，避免给后端送无谓请求 + 给用户即时反馈。
    // 后端 rate_limit_svc 仍是真实强制；此处只是防误操作 / 自动化脚本。
    const wait = checkLoginLimit(email.trim());
    if (wait > 0) {
      pushToast("warning", `登录失败次数过多，请 ${Math.ceil(wait / 60)} 分钟后再试`);
      return;
    }
    clearLogoutFlag();
    setSubmitting(true);
    try {
      await login(email.trim(), password);
      clearLoginLimit(email.trim());
      pushToast("success", "登录成功");
      // user 变化后由 useEffect 跳转
    } catch (err) {
      recordLoginFailure(email.trim());
      pushToast("error", (err as Error).message);
    } finally {
      setSubmitting(false);
    }
  };

  const submitRegister = async () => {
    const email = regForm.email.trim();
    const name = regForm.name.trim();
    const password = regForm.password;
    const confirm = regForm.confirm;
    const xiaomiEmail = regForm.xiaomi_email.trim().toLowerCase();
    if (!email || !name) {
      pushToast("warning", "账号和姓名不能为空");
      return;
    }
    if (xiaomiEmail) {
      // Mirror backend's accept-list (xiaomi.com / mi.com). If the user types
      // a non-Xiaomi address we fail fast — backend would reject anyway, but
      // a client-side hint avoids round-trip.
      const ok = /^[A-Za-z0-9._\-+]+@(xiaomi|mi)\.com$/i.test(xiaomiEmail);
      if (!ok) {
        pushToast("warning", "小米办公邮箱必须是 @xiaomi.com 或 @mi.com");
        return;
      }
    }
    if (/\s/.test(email)) {
      pushToast("warning", "账号不能包含空格");
      return;
    }
    if (password.length < 10) {
      pushToast("warning", "密码至少 10 位");
      return;
    }
    if (password.length > 128) {
      pushToast("warning", "密码最长 128 位");
      return;
    }
    const classes =
      Number(/[a-z]/.test(password)) +
      Number(/[A-Z]/.test(password)) +
      Number(/[0-9]/.test(password)) +
      Number(/[^A-Za-z0-9]/.test(password));
    if (classes < 3) {
      pushToast("warning", "密码需包含大小写字母 / 数字 / 符号中的任意 3 类");
      return;
    }
    if (password !== confirm) {
      pushToast("warning", "两次输入的密码不一致");
      return;
    }
    // 注册流程**不要**调 clearLogoutFlag()：那个工具是为登录设计的（清掉 ?logout=1
    // 让 bootstrapMe 重新识别用户）。注册成功后我们要让用户停在"待审批"页，
    // 反而需要保留 ?logout=1 抑制 bootstrapMe，避免本地 dev_bypass 把请求当成
    // admin 自动登入并跳到 dashboard。
    setSubmitting(true);
    try {
      const r = await register(email, name, password, xiaomiEmail || undefined);
      pushToast("success", "账号申请已提交，等待管理员审批");
      setSubmittedForApproval({ email, name, message: r.message });
      // Clear form so the user can't accidentally resubmit.
      setRegForm({ email: "", name: "", password: "", confirm: "", xiaomi_email: "" });
    } catch (err) {
      pushToast("error", (err as Error).message);
    } finally {
      setSubmitting(false);
    }
  };

  const aegisTabVisible = methods?.aegis_enabled ?? false;
  const passwordTabVisible = methods?.password_enabled ?? true;
  const registerAllowed = methods?.open_register_enabled ?? false;

  return (
    <div className="login-page">
      <div className="login-bg-grid" />

      <div className="login-card">
        <aside className="login-left">
          <div className="brand">
            <div className="brand-logo">
              <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="#fff" strokeWidth="2.2">
                <path d="M12 2L2 7l10 5 10-5-10-5z" />
                <path d="M2 17l10 5 10-5" />
                <path d="M2 12l10 5 10-5" />
              </svg>
            </div>
            <div>
              <div className="brand-name">
                <span className="brand-accent">ICE</span> Workbench
              </div>
              <div className="brand-tag">v6 多智能体数据工作舱</div>
            </div>
          </div>

          <div className="login-hero-copy">
            <p className="login-kicker">Mission Control</p>
            <h2>把数据、Agent、审批和长任务放进同一个工作流。</h2>
            <p>
              v6 将任务工作区升级为三栏式控制台：左侧管理上下文，中间处理对话，
              右侧追踪执行计划与人工确认。
            </p>
          </div>

          <div className="login-cockpit" aria-hidden="true">
            <div className="cockpit-top">
              <span>Q2 Retention Analysis</span>
              <b>RUNNING</b>
            </div>
            <div className="cockpit-body">
              <div className="cockpit-track">
                <span className="track-dot is-done" />
                <span className="track-line" />
                <span className="track-dot is-active" />
                <span className="track-line" />
                <span className="track-dot" />
              </div>
              <div className="cockpit-steps">
                <div>
                  <strong>Context</strong>
                  <span>Feishu Bitable + CSV</span>
                </div>
                <div>
                  <strong>Agent Plan</strong>
                  <span>SQL → Chart → Summary</span>
                </div>
                <div>
                  <strong>HITL Gate</strong>
                  <span>Waiting for approval</span>
                </div>
              </div>
            </div>
            <div className="cockpit-metrics">
              <div><span>Tasks</span><b>128</b></div>
              <div><span>Agents</span><b>12</b></div>
              <div><span>HITL</span><b>3</b></div>
            </div>
          </div>
        </aside>

        <main className="login-right">
          <p className="login-kicker">Secure Access</p>
          <h1>欢迎回来</h1>
          <p className="login-sub">选择认证方式，进入你的 ICE Workbench。</p>

          <div className="login-tabs">
            {aegisTabVisible && (
              <button
                type="button"
                className={`login-tab ${tab === "aegis" ? "active" : ""}`}
                onClick={() => setTab("aegis")}
              >
                <i className="ph ph-shield-check" aria-hidden="true" />
                米盾
              </button>
            )}
            {passwordTabVisible && (
              <button
                type="button"
                className={`login-tab ${tab === "password" ? "active" : ""}`}
                onClick={() => setTab("password")}
              >
                <i className="ph ph-key" aria-hidden="true" />
                账号密码
              </button>
            )}
          </div>

          {tab === "aegis" && aegisTabVisible && (
            <div className="login-pane">
              {justLoggedOut ? (
                <div className="login-hint info">
                  <div className="lh-title">已退出登录</div>
                  <div className="lh-body">
                    你已安全登出。若需继续使用米盾账号，点击下方重新验证。
                  </div>
                  <button
                    className="btn-primary login-submit"
                    type="button"
                    onClick={retryAegis}
                  >
                    重新登录
                  </button>
                </div>
              ) : checking ? (
                <div className="login-hint">
                  <div className="lh-body">正在通过米盾代理验证身份…</div>
                </div>
              ) : (
                <div className="login-hint warn">
                  <div className="lh-title">未检测到米盾登录态</div>
                  <div className="lh-body">
                    请通过米盾代理域名访问；本地开发可在 backend <code>.env</code> 设置{" "}
                    <code>AEGIS_DEV_BYPASS_EMAIL=admin</code> 后重启。
                  </div>
                  <button
                    className="btn-primary login-submit"
                    type="button"
                    onClick={retryAegis}
                  >
                    重新尝试
                  </button>
                </div>
              )}
            </div>
          )}

          {tab === "password" && passwordTabVisible && (
            <div className="login-pane">
              {registerAllowed && (
                <div className="login-mode-switch" role="tablist">
                  <button
                    type="button"
                    role="tab"
                    aria-selected={pwMode === "login"}
                    className={`login-mode-btn ${pwMode === "login" ? "active" : ""}`}
                    onClick={() => setPwMode("login")}
                  >
                    登录
                  </button>
                  <button
                    type="button"
                    role="tab"
                    aria-selected={pwMode === "register"}
                    className={`login-mode-btn ${pwMode === "register" ? "active" : ""}`}
                    onClick={() => setPwMode("register")}
                  >
                    注册
                  </button>
                </div>
              )}

              {submittedForApproval && pwMode === "register" ? (
                <div className="login-form" style={{ gap: 14 }}>
                  <div
                    style={{
                      padding: "14px 16px",
                      borderRadius: 10,
                      background: "rgba(250, 204, 21, 0.12)",
                      border: "1px solid rgba(250, 204, 21, 0.4)",
                      color: "var(--text-strong, #fef3c7)",
                      fontSize: 13,
                      lineHeight: 1.6,
                    }}
                  >
                    <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 6 }}>
                      账号申请已提交，等待管理员审批
                    </div>
                    <div>
                      账号：<code>{submittedForApproval.email}</code>
                      <br />
                      申请人：{submittedForApproval.name}
                    </div>
                    <div style={{ marginTop: 8, color: "var(--text-muted)" }}>
                      {submittedForApproval.message}
                    </div>
                  </div>
                  <button
                    className="btn-primary login-submit"
                    type="button"
                    onClick={() => {
                      setSubmittedForApproval(null);
                      setPwMode("login");
                    }}
                  >
                    回到登录页
                  </button>
                  <button
                    className="btn-secondary login-submit"
                    type="button"
                    onClick={() => setSubmittedForApproval(null)}
                  >
                    再申请一个账号
                  </button>
                </div>
              ) : pwMode === "login" ? (
                <form
                  className="login-form"
                  onSubmit={(e) => {
                    e.preventDefault();
                    submitPassword(form.email, form.password);
                  }}
                >
                  <label className="login-field">
                    <span>账号（邮箱或用户名）</span>
                    <input
                      type="text"
                      autoComplete="username"
                      value={form.email}
                      onChange={(e) => setForm({ ...form, email: e.target.value })}
                      placeholder="账号或邮箱"
                    />
                  </label>
                  <label className="login-field">
                    <span>密码</span>
                    <input
                      type="password"
                      autoComplete="current-password"
                      value={form.password}
                      onChange={(e) => setForm({ ...form, password: e.target.value })}
                      placeholder="输入密码"
                    />
                  </label>
                  <button
                    className="btn-primary login-submit"
                    type="submit"
                    disabled={submitting}
                  >
                    {submitting ? "登录中…" : "登录"}
                  </button>
                  {registerAllowed && (
                    <div className="login-foot" style={{ textAlign: "center", marginTop: 12 }}>
                      还没有账号？
                      <a
                        href="#"
                        onClick={(e) => {
                          e.preventDefault();
                          setPwMode("register");
                        }}
                      >
                        去注册
                      </a>
                    </div>
                  )}
                </form>
              ) : (
                <form
                  className="login-form"
                  onSubmit={(e) => {
                    e.preventDefault();
                    submitRegister();
                  }}
                >
                  <label className="login-field">
                    <span>账号（邮箱或用户名）</span>
                    <input
                      type="text"
                      autoComplete="username"
                      value={regForm.email}
                      onChange={(e) => setRegForm({ ...regForm, email: e.target.value })}
                      placeholder="不含空格，最长 120 位"
                    />
                  </label>
                  <label className="login-field">
                    <span>姓名</span>
                    <input
                      type="text"
                      autoComplete="name"
                      value={regForm.name}
                      onChange={(e) => setRegForm({ ...regForm, name: e.target.value })}
                      placeholder="展示用的名字"
                    />
                  </label>
                  <label className="login-field">
                    <span>小米办公邮箱（可选）</span>
                    <input
                      type="email"
                      autoComplete="email"
                      value={regForm.xiaomi_email}
                      onChange={(e) =>
                        setRegForm({ ...regForm, xiaomi_email: e.target.value })
                      }
                      placeholder="xxx@xiaomi.com — 用于飞书报告自动给你加权限"
                    />
                  </label>
                  <label className="login-field">
                    <span>密码</span>
                    <input
                      type="password"
                      autoComplete="new-password"
                      value={regForm.password}
                      onChange={(e) => setRegForm({ ...regForm, password: e.target.value })}
                      placeholder="至少 10 位，含大小写/数字/符号 3 类"
                    />
                  </label>
                  <PasswordRuleList
                    password={regForm.password}
                    email={regForm.email}
                    name={regForm.name}
                  />
                  <label className="login-field">
                    <span>确认密码</span>
                    <input
                      type="password"
                      autoComplete="new-password"
                      value={regForm.confirm}
                      onChange={(e) => setRegForm({ ...regForm, confirm: e.target.value })}
                      placeholder="再输一次"
                    />
                  </label>
                  <button
                    className="btn-primary login-submit"
                    type="submit"
                    disabled={submitting}
                  >
                    {submitting ? "创建中…" : "创建账号"}
                  </button>
                  <div className="login-foot" style={{ textAlign: "center", marginTop: 12 }}>
                    已有账号？
                    <a
                      href="#"
                      onClick={(e) => {
                        e.preventDefault();
                        setPwMode("login");
                      }}
                    >
                      去登录
                    </a>
                  </div>
                </form>
              )}
            </div>
          )}

          {toggles && !toggles.feishu_enabled && tab === "aegis" && (
            <div className="login-foot">
              提示：如需启用飞书 OAuth，请在后端 <code>.env</code> 配置{" "}
              <code>FEISHU_APP_ID / FEISHU_APP_SECRET</code>。
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
