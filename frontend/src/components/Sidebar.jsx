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

function NoteRow({ note }) {
  return (
    <div className="note-row">
      <span className="note-name" title={note.source}>{note.source}</span>
      <span className="note-chunks">{note.chunks}개 조각</span>
    </div>
  );
}

export default function Sidebar({
  weakTopics,
  notes,
  onReset,
  onUpload,
  uploading,
  uploadError,
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
      <div
        className={`sidebar-overlay ${isOpen ? "visible" : ""}`}
        onClick={onClose}
      />
      <aside className={`sidebar ${isOpen ? "sidebar-open" : ""}`}>
        <div className="sidebar-head">
          <div className="sidebar-title">노트</div>
          <button
            type="button"
            className="sidebar-close"
            aria-label="닫기"
            onClick={onClose}
          >
            ×
          </button>
        </div>

        <label className="upload-button">
          {uploading ? "업로드 중..." : "노트 업로드"}
          <input
            type="file"
            accept=".pdf,.md,.txt"
            multiple
            onChange={handleFileChange}
            disabled={uploading}
            hidden
          />
        </label>
        {uploadError && <div className="upload-error">{uploadError}</div>}

        {notes.length === 0 ? (
          <div className="empty-state">
            아직 업로드한 노트가 없어요.
            <br />
            PDF, 마크다운, 텍스트 파일을 올려보세요.
          </div>
        ) : (
          <div className="note-list">
            {notes.map((note) => (
              <NoteRow key={note.source} note={note} />
            ))}
          </div>
        )}

        <hr className="divider" />

        <div className="sidebar-title">약점 주제</div>
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
