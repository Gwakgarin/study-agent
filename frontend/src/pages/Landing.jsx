import { Link } from "react-router-dom";
import Logo from "../components/Logo.jsx";

const FEATURES = [
  {
    title: "노트 기반 답변",
    desc: "업로드한 노트에서 관련 내용을 검색해 근거 있는 답변만 제공해요. 노트에 없는 내용은 모른다고 솔직히 말해요.",
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="11" cy="11" r="6.5" />
        <path d="M20 20L15.5 15.5" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    title: "약점 자동 추적",
    desc: "퀴즈에서 틀린 주제를 자동으로 기록하고, 오답률을 계산해서 우선순위를 매겨요.",
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="12" cy="12" r="8.5" />
        <circle cx="12" cy="12" r="4.5" />
        <circle cx="12" cy="12" r="0.9" fill="currentColor" stroke="none" />
      </svg>
    ),
  },
  {
    title: "맞춤 퀴즈 생성",
    desc: "약점 주제를 우선으로 노트 내용을 바탕으로 객관식 퀴즈를 만들어 바로 복습할 수 있어요.",
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M12 17.5v.01" strokeLinecap="round" />
        <path d="M9.2 9.3a2.8 2.8 0 1 1 3.9 2.6c-.9.4-1.4 1.1-1.4 2" strokeLinecap="round" />
        <rect x="3.5" y="3.5" width="17" height="17" rx="5" />
      </svg>
    ),
  },
];

const STEPS = [
  { n: "01", title: "노트를 색인", desc: "PDF나 텍스트로 정리한 공부 노트를 검색 가능하게 색인해요." },
  { n: "02", title: "질문하고 퀴즈 풀기", desc: "궁금한 내용을 물어보거나 퀴즈를 요청해서 이해도를 확인해요." },
  { n: "03", title: "약점 우선 복습", desc: "오답률이 높은 주제가 자동으로 다음 퀴즈에 먼저 등장해요." },
];

export default function Landing() {
  return (
    <div className="landing">
      <nav className="navbar">
        <Logo size={28} />
        <div className="nav-links">
          <a href="#features">기능</a>
          <a href="#how">사용법</a>
        </div>
        <Link to="/app" className="btn-primary btn-small">
          시작하기
        </Link>
      </nav>

      <header className="hero-landing">
        <div className="hero-copy">
          <div className="eyebrow">AI 학습 코치</div>
          <h1>
            노트를 다시 훑어보는
            <br />
            가장 똑똑한 방법
          </h1>
          <p>
            Recap은 여러분의 공부 노트를 검색해서 답하고, 틀린 주제를 기억해뒀다가
            다음 퀴즈에서 우선 출제하는 학습 에이전트예요.
          </p>
          <div className="hero-actions">
            <Link to="/app" className="btn-primary">
              무료로 시작하기
            </Link>
            <a href="#features" className="btn-ghost">
              기능 살펴보기
            </a>
          </div>
        </div>

        <div className="hero-preview">
          <div className="preview-card">
            <div className="preview-row preview-row-assistant">
              <div className="preview-bubble">이 개념은 노트 3페이지에 자세히 나와요. 요약하면...</div>
            </div>
            <div className="preview-row preview-row-user">
              <div className="preview-bubble preview-bubble-user">퀴즈 하나 내줘</div>
            </div>
            <div className="preview-row preview-row-assistant">
              <div className="preview-bubble">지난번 틀렸던 "확산 모델" 주제로 문제를 냈어요.</div>
            </div>
          </div>
        </div>
      </header>

      <section className="features" id="features">
        <h2>학습을 도와주는 세 가지 방법</h2>
        <div className="features-grid">
          {FEATURES.map((f) => (
            <div className="feature-card" key={f.title}>
              <div className="feature-icon">{f.icon}</div>
              <h3>{f.title}</h3>
              <p>{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="steps" id="how">
        <h2>사용 방법</h2>
        <div className="steps-grid">
          {STEPS.map((s) => (
            <div className="step-card" key={s.n}>
              <div className="step-number">{s.n}</div>
              <h3>{s.title}</h3>
              <p>{s.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <footer className="landing-footer">
        <Logo size={22} />
        <span>© 2026 Recap. 개인 학습을 위한 프로젝트입니다.</span>
      </footer>
    </div>
  );
}
