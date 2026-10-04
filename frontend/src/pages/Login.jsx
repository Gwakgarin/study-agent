import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import Logo from "../components/Logo.jsx";
import { fetchAuthConfig, login, signup } from "../api.js";

export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const [mode, setMode] = useState("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [signupCode, setSignupCode] = useState("");
  const [codeRequired, setCodeRequired] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchAuthConfig()
      .then((config) => setCodeRequired(config.signup_code_required))
      .catch(() => {});
  }, []);

  const isSignup = mode === "signup";

  function switchMode(next) {
    setMode(next);
    setError(null);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      if (isSignup) {
        await signup(username.trim(), password, signupCode.trim());
      } else {
        await login(username.trim(), password);
      }
      navigate(location.state?.from || "/app", { replace: true });
    } catch (err) {
      setError(err.message || "잠시 후 다시 시도해주세요.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="projects-page">
      <nav className="navbar">
        <Link to="/">
          <Logo size={28} />
        </Link>
      </nav>

      <div className="auth-card">
        <div className="auth-tabs" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={!isSignup}
            className={!isSignup ? "active" : ""}
            onClick={() => switchMode("login")}
          >
            로그인
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={isSignup}
            className={isSignup ? "active" : ""}
            onClick={() => switchMode("signup")}
          >
            회원가입
          </button>
        </div>

        <p className="auth-sub">
          {isSignup
            ? "내 과목과 노트, 오답 기록은 내 계정에서만 보여요."
            : "이어서 공부할 계정으로 들어오세요."}
        </p>

        <form className="auth-form" onSubmit={handleSubmit}>
          <label>
            아이디
            <input
              type="text"
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="영문, 숫자, _ 3~20자"
              required
            />
          </label>
          <label>
            비밀번호
            <input
              type="password"
              autoComplete={isSignup ? "new-password" : "current-password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={isSignup ? "8자 이상" : ""}
              required
            />
          </label>
          {isSignup && codeRequired && (
            <label>
              가입 코드
              <input
                type="text"
                value={signupCode}
                onChange={(e) => setSignupCode(e.target.value)}
                placeholder="받은 가입 코드"
                required
              />
            </label>
          )}
          {error && <div className="error-banner">{error}</div>}
          <button type="submit" className="btn-primary" disabled={submitting}>
            {submitting ? "잠시만요..." : isSignup ? "가입하고 시작하기" : "로그인"}
          </button>
        </form>
      </div>
    </div>
  );
}
