export default function ChatMessage({ role, content }) {
  const isUser = role === "user";
  return (
    <div className={`chat-row ${isUser ? "chat-row-user" : "chat-row-assistant"}`}>
      <div className="avatar">{isUser ? "나" : "AI"}</div>
      <div className="bubble">{content}</div>
    </div>
  );
}
