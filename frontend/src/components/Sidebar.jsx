function rateColor(rate) {
  if (rate >= 0.6) return "var(--danger)";
  if (rate >= 0.3) return "var(--warning)";
  return "var(--good)";
}

function WeakTopicCard({ topic, onPractice, busy }) {
  const color = rateColor(topic.wrong_rate);
  return (
    <div className="weak-topic-card">
      <div className="topic-row">
        <span className="topic-name">{topic.topic}</span>
        <span className="topic-rate" style={{ color }}>
          오답 {Math.round(topic.wrong_rate * 100)}%
        </span>
      </div>
      <div className="bar-track">
        <div className="bar-fill" style={{ width: `${topic.wrong_rate * 100}%`, background: color }} />
      </div>
      <div className="topic-foot">
        <span className="topic-meta">
          {topic.attempts}번 중 {topic.wrong}번 틀림
        </span>
        <button type="button" className="practice-button" onClick={() => onPractice(topic.topic)} disabled={busy}>
          다시 풀기
        </button>
      </div>
    </div>
  );
}

function NoteRow({ note }) {
  return (
    <div className="note-row">
      <span className="note-name" title={note.source}>
        {note.source}
      </span>
      <span className="note-chunks">{note.chunks}개 조각</span>
    </div>
  );
}

export default function Sidebar({
  weakTopics,
  reviewTopics,
  notes,
  onReset,
  onUpload,
  onPractice,
  uploading,
  uploadError,
  busy,
  isOpen,
  onClose,
}) {
  function handleFileChange(e) {
    const files = e.target.files;
    if (files && files.length > 0) {
      onUpload(files);
    }
    e.target.value = "";
  }

  return (
    <>
      <div className={`sidebar-overlay ${isOpen ? "visible" : ""}`} onClick={onClose} />
      <aside className={`sidebar ${isOpen ? "sidebar-open" : ""}`} aria-label="학습 현황">
        <div className="sidebar-head">
          <div className="sidebar-title">오늘 복습</div>
          <button type="button" className="sidebar-close" aria-label="닫기" onClick={onClose}>
            ×
          </button>
        </div>
        {reviewTopics.length === 0 ? (
          <div className="empty-state">오늘 복습할 주제는 없어요. 퀴즈를 풀면 복습 날짜가 잡혀요.</div>
        ) : (
          <div className="review-list">
            {reviewTopics.map((t) => (
              <button
                key={t.topic}
                type="button"
                className="review-item"
                onClick={() => onPractice(t.topic)}
                disabled={busy}
              >
                <span>{t.topic}</span>
                <span className="review-go">퀴즈 풀기 →</span>
              </button>
            ))}
          </div>
        )}

        <hr className="divider" />

        <div className="sidebar-title">약점 주제</div>
        {weakTopics.length === 0 ? (
          <div className="empty-state">아직 틀린 문제가 없어요. 퀴즈를 풀면 여기에 쌓여요.</div>
        ) : (
          weakTopics.map((topic) => (
            <WeakTopicCard key={topic.topic} topic={topic} onPractice={onPractice} busy={busy} />
          ))
        )}

        <hr className="divider" />

        <div className="sidebar-title">노트 {notes.length > 0 && <span className="count">{notes.length}</span>}</div>
        <label className={`upload-button ${uploading ? "is-busy" : ""}`}>
          {uploading ? "노트를 정리하는 중..." : "+ 노트 올리기"}
          <input type="file" accept=".pdf,.md,.txt" multiple onChange={handleFileChange} disabled={uploading} hidden />
        </label>
        <div className="upload-hint">PDF · MD · TXT, 파일당 5MB까지</div>
        {uploadError && (
          <div className="upload-error" role="alert">
            {uploadError}
          </div>
        )}
        {notes.length > 0 && (
          <div className="note-list">
            {notes.map((note) => (
              <NoteRow key={note.source} note={note} />
            ))}
          </div>
        )}

        <hr className="divider" />
        <button className="reset-button" onClick={onReset} disabled={busy}>
          대화 새로 시작
        </button>
      </aside>
    </>
  );
}
