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
  const [passwordConfirm, setPasswordConfirm] = useState("");
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
  const tooShort = isSignup && password.length > 0 && password.length < 8;
  const mismatch = isSignup && passwordConfirm.length > 0 && password !== passwordConfirm;

  function switchMode(next) {
    setMode(next);
    setError(null);
    setPasswordConfirm("");
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (submitting) return;
    if (isSignup && password !== passwordConfirm) {
      setError("비밀번호가 서로 달라요. 다시 확인해주세요.");
      return;
    }
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
              aria-invalid={tooShort || undefined}
              aria-describedby={tooShort ? "password-hint" : undefined}
              required
            />
            {tooShort && (
              <span id="password-hint" className="field-hint">
                8자 이상 입력해주세요. ({password.length}/8)
              </span>
            )}
          </label>
          {isSignup && (
            <label>
              비밀번호 확인
              <input
                type="password"
                autoComplete="new-password"
                value={passwordConfirm}
                onChange={(e) => setPasswordConfirm(e.target.value)}
                placeholder="한 번 더 입력"
                aria-invalid={mismatch || undefined}
                aria-describedby="password-confirm-hint"
                required
              />
              {passwordConfirm.length > 0 && (
                <span id="password-confirm-hint" className={`field-hint ${mismatch ? "" : "ok"}`}>
                  {mismatch ? "비밀번호가 서로 달라요." : "비밀번호가 일치해요."}
                </span>
              )}
            </label>
          )}
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
          <button
            type="submit"
            className="btn-primary"
            disabled={submitting || (isSignup && (tooShort || mismatch || !passwordConfirm))}
          >
            {submitting ? "잠시만요..." : isSignup ? "가입하고 시작하기" : "로그인"}
          </button>
        </form>
      </div>
    </div>
  );
}
