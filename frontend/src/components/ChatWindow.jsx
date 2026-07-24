import { useEffect, useRef, useState } from "react";
import ChatMessage from "./ChatMessage.jsx";

const SUGGESTED_PROMPTS = [
  "이 노트 요약해줘",
  "퀴즈 하나 내줘",
  "가장 헷갈리는 개념이 뭐야?",
];

function EmptyState({ onPick }) {
  return (
    <div className="chat-empty">
      <div className="chat-empty-title">무엇을 도와드릴까요?</div>
      <p className="chat-empty-subtitle">
        노트 내용을 물어보거나 퀴즈를 요청해보세요.
      </p>
      <div className="prompt-chips">
        {SUGGESTED_PROMPTS.map((p) => (
          <button
            key={p}
            type="button"
            className="prompt-chip"
            onClick={() => onPick(p)}
          >
            {p}
          </button>
        ))}
      </div>
    </div>
  );
}

export default function ChatWindow({ messages, loading, onSend }) {
  const [input, setInput] = useState("");
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  function handleSubmit(e) {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || loading) return;
    onSend(trimmed);
    setInput("");
  }

  return (
    <div className="chat-window">
      <div className="chat-scroll">
        {messages.length === 0 && !loading && (
          <EmptyState onPick={onSend} />
        )}
        {messages.map((m, i) => (
          <ChatMessage key={i} role={m.role} content={m.content} />
        ))}
        {loading && (
          <div className="chat-row chat-row-assistant">
            <div className="avatar">AI</div>
            <div className="bubble typing">
              <span className="dot" />
              <span className="dot" />
              <span className="dot" />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      <form className="chat-input-bar" onSubmit={handleSubmit}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="무엇이 궁금한가요?"
          disabled={loading}
        />
        <button type="submit" disabled={loading || !input.trim()}>
          전송
        </button>
      </form>
    </div>
  );
}
