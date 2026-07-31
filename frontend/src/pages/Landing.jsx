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

const PROBLEMS = [
  {
    title: "노트를 다시 펼쳐볼 시간이 없어요",
    desc: "정리는 해뒀는데 시험 전날에야 훑어보게 되고, 결국 중요한 부분을 놓쳐요.",
  },
  {
    title: "뭘 모르는지 스스로는 잘 몰라요",
    desc: "안다고 생각했던 개념이 막상 문제로 나오면 헷갈리는 경우가 많아요.",
  },
  {
    title: "같은 실수를 반복해요",
    desc: "한 번 틀린 주제를 따로 챙기지 않으면 다음에도 똑같이 틀려요.",
  },
  {
    title: "검색만으로는 부족해요",
    desc: "노트 어딘가에 있다는 건 알아도, 그걸 다시 문제로 풀어보긴 귀찮아요.",
  },
];

const FAQS = [
  {
    q: "어떤 형식의 노트를 올릴 수 있나요?",
    a: "PDF, 마크다운(.md), 일반 텍스트(.txt) 파일을 올릴 수 있어요. 업로드하면 자동으로 문단 단위로 나눠 검색 가능한 형태로 색인돼요.",
  },
  {
    q: "퀴즈는 어떻게 만들어지나요?",
    a: "색인된 노트 내용 중 관련 있는 부분을 찾아 그 내용을 바탕으로 객관식 문제를 생성해요. 노트에 없는 내용으로는 문제를 내지 않아요.",
  },
  {
    q: "약점 주제는 어떻게 정해지나요?",
    a: "퀴즈를 풀 때마다 주제별 정답/오답을 기록하고, 오답률이 높은 주제를 우선순위로 매겨 다음 퀴즈에 먼저 출제해요.",
  },
  {
    q: "제 노트가 다른 곳으로 전송되나요?",
    a: "아니요. 노트는 로컬 환경에서 검색 인덱스로만 사용되고, 답변/퀴즈 생성을 위해서만 필요한 부분이 모델 호출에 쓰여요.",
  },
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

      <section className="problem">
        <h2>이런 경험, 있으신가요?</h2>
        <p className="problem-sub">
          공부 노트는 쌓여가는데, 정작 시험 볼 땐 뭘 아는지 모르는지 헷갈리는 순간들이에요.
        </p>
        <div className="problem-grid">
          {PROBLEMS.map((p, i) => (
            <div className="problem-card" key={p.title}>
              <div className="problem-mark">{i + 1}</div>
              <div>
                <h3>{p.title}</h3>
                <p>{p.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

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

      <section className="faq">
        <h2>자주 묻는 질문</h2>
        <div className="faq-list">
          {FAQS.map((f) => (
            <div className="faq-item" key={f.q}>
              <h3>{f.q}</h3>
              <p>{f.a}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="final-cta">
        <h2>오늘부터 노트를 다시 훑어보세요</h2>
        <p>가입 없이 바로 시작해서, 첫 질문과 첫 퀴즈까지 1분이면 충분해요.</p>
        <Link to="/app" className="btn-primary">
          무료로 시작하기
        </Link>
      </section>

      <footer className="landing-footer">
        <Logo size={22} />
        <span>© 2026 Recap. 개인 학습을 위한 프로젝트입니다.</span>
      </footer>
    </div>
  );
}
