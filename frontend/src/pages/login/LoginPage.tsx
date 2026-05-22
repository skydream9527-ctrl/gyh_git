import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuthStore } from "@/stores/authStore";
import { authApi, sysApi } from "@/api/endpoints";
import type { GlobalToggles } from "@/types/api";
import { useUIStore } from "@/stores/uiStore";
import "./Login.css";

/**
 * 两种登录方式（后端 /auth/methods 控制可见性）：
 *  ① 米盾代理：浏览器 cookie 由代理注入，进入页面自动 bootstrapMe。
 *  ② 账号密码：POST /auth/login 换 JWT。
 */

type Tab = "aegis" | "password";

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
  const [regForm, setRegForm] = useState({ email: "", name: "", password: "", confirm: "" });
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
    clearLogoutFlag();
    setSubmitting(true);
    try {
      await login(email.trim(), password);
      pushToast("success", "登录成功");
      // user 变化后由 useEffect 跳转
    } catch (err) {
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
    if (!email || !name) {
      pushToast("warning", "账号和姓名不能为空");
      return;
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
      const r = await register(email, name, password);
      pushToast("success", "账号申请已提交，等待管理员审批");
      setSubmittedForApproval({ email, name, message: r.message });
      // Clear form so the user can't accidentally resubmit.
      setRegForm({ email: "", name: "", password: "", confirm: "" });
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
      <div className="login-orb login-orb-1" />
      <div className="login-orb login-orb-2" />

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
                <span className="brand-accent">ICE</span> Data Workbench
              </div>
              <div className="brand-tag">AI 数据工作流工作台</div>
            </div>
          </div>
          <div className="loop-anim">
            <div className="loop-step">
              <div className="dot user" />
              <div className="loop-text">用户：上周新版本留存…</div>
            </div>
            <div className="loop-arrow">↓</div>
            <div className="loop-step">
              <div className="dot tool" />
              <div className="loop-text">⚡ Tool: SQL → Skill → 图表</div>
            </div>
            <div className="loop-arrow">↓</div>
            <div className="loop-step">
              <div className="dot agent" />
              <div className="loop-text">📊 Agent：D7 留存 +5.6pp</div>
            </div>
          </div>
        </aside>

        <main className="login-right">
          <h1>登录</h1>
          <p className="login-sub">两种登录方式任选其一</p>

          <div className="login-tabs">
            {aegisTabVisible && (
              <button
                type="button"
                className={`login-tab ${tab === "aegis" ? "active" : ""}`}
                onClick={() => setTab("aegis")}
              >
                🛡 米盾
              </button>
            )}
            {passwordTabVisible && (
              <button
                type="button"
                className={`login-tab ${tab === "password" ? "active" : ""}`}
                onClick={() => setTab("password")}
              >
                🔑 账号密码
              </button>
            )}
          </div>

          {tab === "aegis" && aegisTabVisible && (
            <div className="login-pane">
              {justLoggedOut ? (
                <div className="login-hint info">
                  <div className="lh-title">👋 已退出登录</div>
                  <div className="lh-body">
                    你已安全登出。若需继续使用米盾账号，点击下方重新验证。
                  </div>
                  <button
                    className="btn-primary login-submit"
                    type="button"
                    onClick={retryAegis}
                  >
                    🔁 重新登录
                  </button>
                </div>
              ) : checking ? (
                <div className="login-hint">
                  <div className="lh-body">正在通过米盾代理验证身份…</div>
                </div>
              ) : (
                <div className="login-hint warn">
                  <div className="lh-title">🔐 未检测到米盾登录态</div>
                  <div className="lh-body">
                    请通过米盾代理域名访问；本地开发可在 backend <code>.env</code> 设置{" "}
                    <code>AEGIS_DEV_BYPASS_EMAIL=admin</code> 后重启。
                  </div>
                  <button
                    className="btn-primary login-submit"
                    type="button"
                    onClick={retryAegis}
                  >
                    🔁 重新尝试
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
                      🕓 账号申请已提交，等待管理员审批
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
                    <span>密码</span>
                    <input
                      type="password"
                      autoComplete="new-password"
                      value={regForm.password}
                      onChange={(e) => setRegForm({ ...regForm, password: e.target.value })}
                      placeholder="至少 10 位，含大小写/数字/符号 3 类"
                    />
                  </label>
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
