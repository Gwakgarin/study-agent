function rateColor(rate) {
  if (rate >= 0.6) return "#E74C3C";
  if (rate >= 0.3) return "#E67E22";
  return "#27AE60";
}

function WeakTopicCard({ topic }) {
  const color = rateColor(topic.wrong_rate);
  return (
    <div className="weak-topic-card">
      <div className="topic-row">
        <span className="topic-name">{topic.topic}</span>
        <span className="topic-rate" style={{ color }}>
          {Math.round(topic.wrong_rate * 100)}%
        </span>
      </div>
      <div className="bar-track">
        <div
          className="bar-fill"
          style={{ width: `${topic.wrong_rate * 100}%`, background: color }}
        />
      </div>
      <div className="topic-meta">
        오답 {topic.wrong} / 시도 {topic.attempts}
      </div>
    </div>
  );
}

export default function Sidebar({ weakTopics, onReset, isOpen, onClose }) {
  return (
    <>
      <div
        className={`sidebar-overlay ${isOpen ? "visible" : ""}`}
        onClick={onClose}
      />
      <aside className={`sidebar ${isOpen ? "sidebar-open" : ""}`}>
        <div className="sidebar-head">
          <div className="sidebar-title">약점 주제</div>
          <button
            type="button"
            className="sidebar-close"
            aria-label="닫기"
            onClick={onClose}
          >
            ×
          </button>
        </div>
        {weakTopics.length === 0 ? (
          <div className="empty-state">
            아직 기록된 오답이 없어요.
            <br />
            퀴즈를 풀어보면 여기에 쌓여요.
          </div>
        ) : (
          weakTopics.map((topic) => (
            <WeakTopicCard key={topic.topic} topic={topic} />
          ))
        )}
        <hr className="divider" />
        <button className="reset-button" onClick={onReset}>
          대화 초기화
        </button>
      </aside>
    </>
  );
}
