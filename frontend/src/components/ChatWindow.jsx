import { useEffect, useRef, useState } from "react";
import ChatMessage from "./ChatMessage.jsx";

const SUGGESTED_PROMPTS = ["이 노트 핵심만 요약해줘", "퀴즈 하나 내줘", "내가 자주 틀리는 개념이 뭐야?"];

function Onboarding({ onUpload, uploading }) {
  function handleFiles(e) {
    if (e.target.files?.length) onUpload(e.target.files);
    e.target.value = "";
  }
  return (
    <div className="chat-empty">
      <div className="chat-empty-title">노트를 올리면 바로 시작할 수 있어요</div>
      <ol className="onboarding-steps">
        <li>
          <strong>노트 올리기</strong>
          <span>PDF, 마크다운, 텍스트 파일을 올리면 검색할 수 있게 정리해요.</span>
        </li>
        <li>
          <strong>물어보기</strong>
          <span>답에는 참고한 노트가 함께 표시돼요.</span>
        </li>
        <li>
          <strong>퀴즈 풀기</strong>
          <span>틀린 주제는 약점으로 쌓이고, 복습할 날짜에 다시 알려줘요.</span>
        </li>
      </ol>
      <label className={`btn-primary upload-cta ${uploading ? "is-busy" : ""}`}>
        {uploading ? "노트를 정리하는 중..." : "노트 올리기"}
        <input type="file" accept=".pdf,.md,.txt" multiple hidden onChange={handleFiles} disabled={uploading} />
      </label>
    </div>
  );
}

function Suggestions({ onPick }) {
  return (
    <div className="chat-empty">
      <div className="chat-empty-title">무엇부터 해볼까요?</div>
      <p className="chat-empty-subtitle">노트 내용을 물어보거나 퀴즈를 요청해보세요.</p>
      <div className="prompt-chips">
        {SUGGESTED_PROMPTS.map((p) => (
          <button key={p} type="button" className="prompt-chip" onClick={() => onPick(p)}>
            {p}
          </button>
        ))}
      </div>
    </div>
  );
}

export default function ChatWindow({ messages, busy, onSend, onAnswerQuiz, hasNotes, onUpload, uploading }) {
  const [input, setInput] = useState("");
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  async function handleSubmit(e) {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || busy) return;
    setInput("");
    const sent = await onSend(trimmed);
    // Put the text back so a failed message can be resent without retyping it.
    if (sent === false) setInput(trimmed);
  }

  return (
    <div className="chat-window">
      <div className="chat-scroll" aria-live="polite">
        {messages.length === 0 &&
          (hasNotes ? <Suggestions onPick={onSend} /> : <Onboarding onUpload={onUpload} uploading={uploading} />)}
        {messages.map((m, i) => (
          <ChatMessage key={i} message={m} onAnswerQuiz={onAnswerQuiz} />
        ))}
        <div ref={bottomRef} />
      </div>
      <form className="chat-input-bar" onSubmit={handleSubmit}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={hasNotes ? "무엇이 궁금한가요?" : "노트를 올린 뒤 질문해보세요"}
          disabled={busy}
          aria-label="메시지"
        />
        <button type="submit" disabled={busy || !input.trim()}>
          전송
        </button>
      </form>
    </div>
  );
}
