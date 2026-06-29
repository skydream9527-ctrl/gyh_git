import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "@/stores/authStore";

export default function Login() {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");

  const { login, register, loading, error, clearError } = useAuthStore();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();
    try {
      if (mode === "login") {
        await login(username, password);
      } else {
        await register(username, password, name);
      }
      navigate("/workbench");
    } catch {
      // error already in store
    }
  };

  return (
    <div className="login-page">
      <div className="login-box">
        <div className="eyebrow">ICE-DATA-WORK</div>
        <h1>{mode === "login" ? "登录" : "注册"}</h1>
        <p className="subtle">
          {mode === "login"
            ? "使用用户名密码登录工作台"
            : "创建新账号并开始使用"}
        </p>

        {error && <div className="card err">{error}</div>}

        <form onSubmit={handleSubmit} className="login-form">
          <label>
            用户名
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="admin"
              required
              autoFocus
            />
          </label>

          {mode === "register" && (
            <label>
              昵称
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="显示名称"
              />
            </label>
          )}

          <label>
            密码
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••"
              required
            />
          </label>

          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? "处理中…" : mode === "login" ? "登录" : "注册"}
          </button>
        </form>

        <div className="login-switch">
          {mode === "login" ? (
            <span>
              没有账号？{" "}
              <button className="link-btn" onClick={() => setMode("register")}>
                注册
              </button>
            </span>
          ) : (
            <span>
              已有账号？{" "}
              <button className="link-btn" onClick={() => setMode("login")}>
                登录
              </button>
            </span>
          )}
        </div>

        <div className="login-hint">
          <small>开发环境：admin / admin123 或 test / test123</small>
        </div>
      </div>
    </div>
  );
}
