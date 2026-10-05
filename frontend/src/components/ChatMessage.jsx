import Markdown from "react-markdown";
import QuizCard from "./QuizCard.jsx";
import Sources from "./Sources.jsx";

export default function ChatMessage({ message, onAnswerQuiz }) {
  const { role, content, sources, quiz, status, streaming } = message;
  const isUser = role === "user";
  return (
    <div className={`chat-row ${isUser ? "chat-row-user" : "chat-row-assistant"}`}>
      <div className="avatar">{isUser ? "나" : "AI"}</div>
      <div className="message-stack">
        {isUser ? (
          <div className="bubble">{content}</div>
        ) : (
          <>
            {status && !content && (
              <div className="bubble status-bubble" role="status">
                <span className="spinner" aria-hidden="true" />
                {status}
              </div>
            )}
            {content && (
              <div className={`bubble markdown ${streaming ? "is-streaming" : ""}`}>
                <Markdown>{content}</Markdown>
              </div>
            )}
            {quiz && <QuizCard quiz={quiz} onAnswer={onAnswerQuiz} />}
            {sources?.length > 0 && <Sources sources={sources} />}
          </>
        )}
      </div>
    </div>
  );
}
