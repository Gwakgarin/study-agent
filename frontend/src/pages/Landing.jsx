import { Link } from "react-router-dom";
import Logo from "../components/Logo.jsx";

// Numbers from eval/ (SQLD notes, 102 questions, 2 runs); keep in sync with the README.
const STATS = [
  { value: "97.6%", label: "답변 정확도" },
  { value: "97.6%", label: "맞는 노트 찾기" },
  { value: "100%", label: "노트 밖 질문 거절" },
];

const UPLOADS = [
  { tag: "PDF", tone: "pdf", name: "01_데이터모델링.pdf", size: "1.8MB", progress: 100, status: "4조각" },
  { tag: "MD", tone: "md", name: "02_정규화와_성능.md", size: "5KB", progress: 100, status: "5조각" },
  { tag: "DOCX", tone: "docx", name: "03_SQL_기본.docx", size: "640KB", progress: 68, status: "제목 나누는 중 68%" },
];

// Real headings of eval/corpus/02_정규화와_성능.md
const HEADINGS = ["정규화", "반정규화", "슈퍼타입과 서브타입 변환", "분산 데이터베이스", "NULL 속성과 Row Chaining"];

// Follows the SM-2 rule in src/tracker.py: wrong -> next day, two right in a row -> 6 days.
const STEPS = [
  { when: "오늘", big: "틀림", note: "퀴즈에서 틀렸어요", tone: "wrong" },
  { when: "내일", big: "다시 출제", note: "오늘 복습에 올라와요", tone: "due" },
  { when: "두 번 연속 맞히면", big: "6일 뒤", note: "간격이 벌어져요" },
  { when: "또 맞히면", big: "약 2주 뒤", note: "점점 더 길게" },
];

const DAYS = [
  ["화", 11, "wrong"], ["수", 12, "due"], ["목", 13, "due"], ["금", 14], ["토", 15],
  ["일", 16], ["월", 17], ["화", 18], ["수", 19, "due"],
];

function Check() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M5 12l5 5L20 7" />
    </svg>
  );
}

function AppPreview() {
  return (
    <div className="lp-hero-visual" aria-hidden="true">
      <div className="lp-app">
        <div className="lp-app-side">
          <Logo size={18} />
          <div className="lp-app-subjects">
            <span className="active">SQLD 공부</span>
            <span>정보처리기사</span>
            <span>전공 중간고사</span>
          </div>
          <div className="lp-app-notes">
            <small>노트 6</small>
            <span>01_데이터모델링.pdf</span>
            <span>02_정규화와_성능.md</span>
            <span>03_SQL_기본.docx</span>
            <span>04_조인과_서브쿼리.md</span>
          </div>
        </div>
        <div className="lp-app-main">
          <div className="lp-app-title">오늘 다시 볼 주제</div>
          <div className="lp-app-due">
            <div className="due-card now"><small>지금 풀 차례</small><b>윈도우 함수</b><span>어제 틀렸어요</span></div>
            <div className="due-card"><small>오늘</small><b>정규화</b><span>6일 전에 맞혔어요</span></div>
            <div className="due-card"><small>내일</small><b>조인</b><span>오답 20%</span></div>
          </div>
          <div className="lp-app-grid">
            <div className="lp-quiz">
              <small>복습 퀴즈 · 윈도우 함수</small>
              <b>결과 행의 수가 줄어드는 건 어느 쪽일까요?</b>
              <span className="opt">윈도우 함수</span>
              <span className="opt right">GROUP BY 집계<em>정답</em></span>
              <span className="opt">둘 다 그대로예요</span>
              <p>GROUP BY는 그룹마다 한 행으로 묶어서 행 수가 줄어요.</p>
              <small>한 번 더 맞히면 6일 뒤로 넘어가요</small>
            </div>
            <div className="lp-weak">
              <small>약점 주제</small>
              {[["정규화", 60], ["윈도우 함수", 50], ["조인", 20], ["그룹 함수", 10]].map(([name, pct]) => (
                <div key={name}>
                  <div className="row"><span>{name}</span><span>{pct}%</span></div>
                  <div className="bar"><i style={{ width: `${pct}%` }} /></div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
      <div className="lp-float">
        <p>논리적 모델링 단계에서 해요. 중복을 줄이려고 테이블을 나눠요.</p>
        <small>참고한 노트 · 02_정규화와_성능.md</small>
      </div>
    </div>
  );
}

function UploadVisual() {
  return (
    <div className="lp-card lp-upload">
      <div className="lp-upload-list">
        <div className="lp-card-head"><b>노트 올리기</b><small>3개 중 2개 완료</small></div>
        {UPLOADS.map((u) => (
          <div className="lp-file" key={u.name}>
            <div className="row"><span className={`tag ${u.tone}`}>{u.tag}</span><b>{u.name}</b><small>{u.size}</small></div>
            <div className="bar"><i className={u.progress === 100 ? "done" : ""} style={{ width: `${u.progress}%` }} /></div>
            <div className={`status ${u.progress === 100 ? "done" : ""}`}>{u.progress === 100 && <Check />}{u.status}</div>
          </div>
        ))}
        <div className="lp-drop">파일을 끌어다 놓거나 눌러서 추가</div>
      </div>
      <div className="lp-headings">
        <div className="lp-card-head"><b>02_정규화와_성능.md</b><small>제목별로 나눴어요</small></div>
        {HEADINGS.map((h, i) => (
          <div className={`lp-heading ${i === 0 ? "on" : ""}`} key={h}><span>{i + 1}</span>{h}</div>
        ))}
      </div>
    </div>
  );
}

function AnswerVisual() {
  return (
    <div className="lp-card lp-chat">
      <div className="me">정규화는 어느 단계에서 해?</div>
      <div className="bot">
        논리적 모델링 단계에서 해요. 중복을 줄이고 이상 현상을 막으려고 테이블을 나누는 과정이에요.
        <span className="src">참고한 노트 · 02_정규화와_성능.md</span>
        <q>정규화는 논리 데이터 모델링 단계에서 이상 현상을 없애려고…</q>
      </div>
      <div className="me">트랜잭션 격리 수준은?</div>
      <div className="bot muted">올린 노트에는 없는 내용이에요. 지어내지 않을게요.</div>
    </div>
  );
}

function ReviewVisual() {
  return (
    <div className="lp-card lp-review">
      <div className="lp-card-head"><b className="big">윈도우 함수</b><small>SQLD 공부</small></div>
      <div className="lp-steps">
        {STEPS.map((s) => (
          <div className={`lp-step ${s.tone || ""}`} key={s.when}><small>{s.when}</small><b>{s.big}</b><span>{s.note}</span></div>
        ))}
      </div>
      <div className="lp-days">
        {DAYS.map(([d, n, mark], i) => (
          <div className={`lp-day ${i === 0 ? "today" : ""}`} key={n}><span>{d}</span><b>{n}</b><i className={mark || ""} /></div>
        ))}
      </div>
      <div className="lp-legend"><span><i className="wrong" />틀린 날</span><span><i className="due" />다시 나오는 날</span><span className="end">맞힐수록 간격이 길어져요</span></div>
    </div>
  );
}

function Feature({ label, title, desc, points, visual, reverse }) {
  return (
    <section className={`lp-feature ${reverse ? "reverse" : ""}`}>
      <div className="lp-feature-text">
        <div className="lp-label">{label}</div>
        <h2>{title}</h2>
        <p>{desc}</p>
        <ul>{points.map((p) => <li key={p}>{p}</li>)}</ul>
      </div>
      <div className="lp-feature-visual">{visual}</div>
    </section>
  );
}

export default function Landing() {
  return (
    <div className="lp">
      <header className="lp-hero">
        <div className="lp-glow" aria-hidden="true" />
        <nav className="lp-nav">
          <Logo size={24} />
          <div className="lp-nav-links">
            <a href="#features">기능</a>
            <a href="#start">사용 방법</a>
            <Link to="/login">로그인</Link>
            <Link to="/app" className="lp-btn small">시작하기</Link>
          </div>
        </nav>
        <div className="lp-hero-grid">
          <div className="lp-hero-copy">
            <h1>틀린 주제는<br />잊기 전에<br />다시 물어봐요</h1>
            <p>공부 노트를 올리면 그 안에서만 답하고 문제를 내요.<br />다시 볼 때가 되면 먼저 알려줘요.</p>
            <div className="lp-actions">
              <Link to="/app" className="lp-btn">가입 없이 시작하기</Link>
              <a href="#features" className="lp-btn ghost">기능 둘러보기</a>
            </div>
            <div className="lp-stats">
              {STATS.map((s) => <div key={s.label}><b>{s.value}</b><span>{s.label}</span></div>)}
            </div>
            <small className="lp-stats-note">SQLD 노트 6개, 질문 102개로 자체 측정</small>
          </div>
          <AppPreview />
        </div>
      </header>

      <div id="features">
        <Feature
          label="노트 올리기"
          title="노트만 올리면 돼요"
          desc="PDF, Word, 마크다운, 텍스트 파일을 그대로 올리면 recap이 제목 단위로 나눠 읽고 기억해 둬요."
          points={["과목마다 노트를 따로 관리", "제목 단위로 나눠서 검색", "파일당 5MB, 과목당 20개까지"]}
          visual={<UploadVisual />}
        />
        <Feature
          reverse
          label="근거 있는 답변"
          title="내 노트로만 답해요"
          desc="답마다 참고한 노트와 근거 문장을 같이 보여줘요. 노트에 없는 내용이면 지어내지 않고 모른다고 해요."
          points={["답변마다 출처 노트 표시", "노트 밖 질문은 모른다고 답하기", "질문 102개 기준 답변 정확도 97.6%"]}
          visual={<AnswerVisual />}
        />
        <Feature
          label="간격 복습"
          title="틀린 건, 잊기 전에 다시"
          desc="퀴즈에서 틀린 주제는 따로 기억해 뒀다가, 다시 볼 때가 되면 오늘 복습에 올려 둬요."
          points={["틀리면 다음 날 다시", "연속으로 맞힐수록 6일, 약 2주로 간격이 길어져요", "주제별 오답률로 약점 순서 매기기"]}
          visual={<ReviewVisual />}
        />
      </div>

      <section className="lp-start" id="start">
        <h2>지금 바로 써 보세요</h2>
        <p>가입 없이 샘플 과목으로 시작하고, 마음에 들면 기록을 저장하면 돼요.</p>
        <div className="lp-choices">
          <Link to="/app" className="lp-choice recommended">
            <span className="badge">추천</span>
            <span className="icon">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M8 5v14l11-7z" /></svg>
            </span>
            <b>가입 없이 샘플로 체험하기</b>
            <span>SQLD 노트 6개가 미리 들어 있어요. 질문하고, 퀴즈 풀고, 복습이 잡히는 걸 바로 봐요.</span>
            <ol><li>노트에 질문 하나 해 보기</li><li>퀴즈 한 문제 풀어 보기</li><li>오늘 복습에 잡힌 주제 확인</li></ol>
            <em>약 1분 · 가입 없이 바로 시작</em>
          </Link>
          <Link to="/app" className="lp-choice">
            <span className="icon">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M12 16V4M7 9l5-5 5 5" /><path d="M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3" /></svg>
            </span>
            <b>내 노트로 바로 시작</b>
            <span>과목을 만들고 PDF, Word, 마크다운, 텍스트 파일을 올려요.</span>
            <ol><li>과목 이름 정하기</li><li>노트 파일 올리기</li><li>정리되면 바로 질문</li></ol>
            <em className="muted">기록 저장(가입) 후 · 파일당 5MB까지</em>
          </Link>
        </div>
      </section>

      <footer className="lp-footer">
        <Logo size={18} />
        <span>© 2026 recap</span>
      </footer>
    </div>
  );
}
