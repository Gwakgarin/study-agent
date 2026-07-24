import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Logo from "../components/Logo.jsx";
import Sidebar from "../components/Sidebar.jsx";
import ChatWindow from "../components/ChatWindow.jsx";
import { createSession, fetchWeakTopics, resetConversation, sendMessage } from "../api.js";

export default function ChatApp() {
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [weakTopics, setWeakTopics] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    createSession().then((data) => setSessionId(data.session_id));
    refreshWeakTopics();
  }, []);

  function refreshWeakTopics() {
    fetchWeakTopics()
      .then(setWeakTopics)
      .catch(() => setWeakTopics([]));
  }

  async function handleSend(text) {
    if (!sessionId) return;
    setError(null);
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setLoading(true);
    try {
      const data = await sendMessage(sessionId, text);
      setMessages(data.messages);
      refreshWeakTopics();
    } catch (err) {
      setError("응답을 가져오지 못했어요. 서버가 켜져 있는지 확인해주세요.");
    } finally {
      setLoading(false);
    }
  }

  async function handleReset() {
    if (!sessionId) return;
    await resetConversation(sessionId);
    setMessages([]);
    setSidebarOpen(false);
  }

  return (
    <div className="app-shell">
      <Sidebar
        weakTopics={weakTopics}
        onReset={handleReset}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />
      <main className="main-panel">
        <header className="app-topbar">
          <button
            type="button"
            className="sidebar-toggle"
            aria-label="약점 주제 열기"
            onClick={() => setSidebarOpen(true)}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M4 6h16M4 12h16M4 18h16" strokeLinecap="round" />
            </svg>
          </button>
          <Link to="/" className="topbar-logo">
            <Logo size={26} />
          </Link>
          <p className="topbar-subtitle">
            노트를 검색해서 답하고, 약점 주제를 우선 복습하는 학습 파트너
          </p>
        </header>
        {error && <div className="error-banner">{error}</div>}
        <ChatWindow messages={messages} loading={loading} onSend={handleSend} />
      </main>
    </div>
  );
}
