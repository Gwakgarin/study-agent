import { useEffect, useState } from "react";
import { fetchAuthConfig, saveGuest } from "../api.js";

export default function SaveProgress({ onClose, onSaved }) {
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

  useEffect(() => {
    function onKey(e) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  async function handleSubmit(e) {
    e.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      onSaved(await saveGuest(username.trim(), password, signupCode.trim()));
    } catch (err) {
      setError(err.message || "잠시 후 다시 시도해주세요.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <form
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="save-progress-title"
        onClick={(e) => e.stopPropagation()}
        onSubmit={handleSubmit}
      >
        <h2 id="save-progress-title">기록 저장하기</h2>
        <p>
          지금까지 만든 과목과 복습 일정이 그대로 남아요. 저장하면 내 노트도 올릴 수 있어요.
        </p>
        <label htmlFor="save-username">아이디</label>
        <input
          id="save-username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder="영문, 숫자, _ 3~20자"
          autoComplete="username"
          autoFocus
        />
        <label htmlFor="save-password">비밀번호</label>
        <input
          id="save-password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="8자 이상"
          autoComplete="new-password"
        />
        {codeRequired && (
          <>
            <label htmlFor="save-code">가입 코드</label>
            <input id="save-code" value={signupCode} onChange={(e) => setSignupCode(e.target.value)} />
          </>
        )}
        {error && (
          <div className="error-banner" role="alert">
            {error}
          </div>
        )}
        <div className="modal-actions">
          <button type="button" className="btn-ghost" onClick={onClose}>
            나중에
          </button>
          <button type="submit" className="btn-primary" disabled={submitting || !username.trim() || password.length < 8}>
            {submitting ? "저장하는 중..." : "저장하기"}
          </button>
        </div>
      </form>
    </div>
  );
}
