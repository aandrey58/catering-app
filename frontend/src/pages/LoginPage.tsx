import { FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { login as loginApi } from "../api";
import { useAppState } from "../state";

export function LoginPage() {
  const navigate = useNavigate();
  const { setAuth, isDark, setThemeDark } = useAppState();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [notification, setNotification] = useState({ message: "", isError: false, show: false });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    document.body.classList.add("login-page");
    return () => document.body.classList.remove("login-page");
  }, []);

  function showNotification(message: string, isError = false) {
    setNotification({ message, isError, show: true });
    window.setTimeout(() => setNotification((n) => ({ ...n, show: false })), 3000);
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const u = username.trim();
    const p = password;
    if (!u || !p) {
      showNotification("Please fill in all fields", true);
      return;
    }
    setLoading(true);
    try {
      const data = await loginApi(u, p);
      if (data.status === "ok") {
        setAuth(data.login, data.note ?? "", data.access_token);
        showNotification("Login successful!");
        window.setTimeout(() => navigate("/menu"), 1000);
      } else {
        showNotification("Invalid username or password", true);
      }
    } catch {
      showNotification("Invalid username or password", true);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <div className="container">
        <div className="app-header">
          <div className="language-theme">
            <label className="theme-switch">
              <input
                type="checkbox"
                checked={isDark}
                onChange={(e) => setThemeDark(e.target.checked)}
              />
              <span className="theme-slider">
                <span className="theme-thumb">
                  <span className="theme-thumb-icon sun">{"\u2600\uFE0F"}</span>
                  <span className="theme-thumb-icon moon">{"\uD83C\uDF19"}</span>
                </span>
              </span>
            </label>
          </div>
          <div className="navigation-arrows">
            <img
              src={isDark ? "/src/emblem_dark.png" : "/src/emblem.png"}
              alt="Emblem"
              className="emblem-img"
            />
          </div>
          <div />
        </div>

        <div className="login-container">
          <h1 className="login-title">Login</h1>
          <p className="login-subtitle">Please enter your credentials</p>

          <form id="loginForm" onSubmit={onSubmit}>
            <div className="form-group">
              <label className="form-label" htmlFor="username">
                Username
              </label>
              <input
                id="username"
                name="username"
                className="form-input"
                placeholder="Enter username"
                required
                autoComplete="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="password">
                Password
              </label>
              <div className="password-input-wrapper">
                <input
                  id="password"
                  name="password"
                  type={showPassword ? "text" : "password"}
                  className="form-input"
                  placeholder="Enter password"
                  required
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
                <button
                  type="button"
                  className="password-toggle"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  title={showPassword ? "Hide password" : "Show password"}
                  onClick={() => setShowPassword((v) => !v)}
                >
                  <img
                    src={showPassword ? "/src/hide.png" : "/src/look.png"}
                    alt=""
                    id="passwordToggleIcon"
                    style={{ width: 20, height: 20, display: "block" }}
                  />
                </button>
              </div>
            </div>

            <button type="submit" className="login-button">
              Sign In
            </button>
          </form>
        </div>
      </div>

      <div className={`notification${notification.show ? " show" : ""}${notification.isError ? " error" : ""}`}>
        {notification.message}
      </div>

      <div className={`loading-overlay${loading ? " show" : ""}`}>
        <div className="loading-content">
          <div className="loading-spinner" />
          <div className="loading-text">Authenticating...</div>
        </div>
      </div>
    </>
  );
}
