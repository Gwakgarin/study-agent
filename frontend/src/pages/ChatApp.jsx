import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import Logo from "../components/Logo.jsx";
import Sidebar from "../components/Sidebar.jsx";
import ChatWindow from "../components/ChatWindow.jsx";
import {
  AuthRequiredError,
  answerQuiz,
  createSession,
  fetchNotes,
  fetchProjects,
  fetchReview,
  fetchWeakTopics,
  sendMessageStream,
  uploadNotes,
} from "../api.js";

export default function ChatApp() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const [projectName, setProjectName] = useState("");
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [weakTopics, setWeakTopics] = useState([]);
  const [reviewTopics, setReviewTopics] = useState([]);
  const [notes, setNotes] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  function toLogin() {
    navigate("/login", { replace: true, state: { from: `/app/${projectId}` } });
  }

  useEffect(() => {
    createSession(projectId)
      .then((data) => {
        setSessionId(data.session_id);
        setMessages(data.messages);
      })
      .catch((err) => {
        if (err instanceof AuthRequiredError) toLogin();
        // Not this user's project (or it no longer exists): back to the project list.
        else navigate("/app", { replace: true });
      });
    fetchProjects()
      .then((list) => {
        const match = list.find((p) => p.id === projectId);
        if (match) setProjectName(match.name);
      })
      .catch(() => {});
    refreshProgress();
    refreshNotes();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  function refreshProgress() {
    fetchWeakTopics(projectId)
      .then(setWeakTopics)
      .catch(() => setWeakTopics([]));
    fetchReview(projectId)
      .then(setReviewTopics)
      .catch(() => setReviewTopics([]));
  }

  function refreshNotes() {
    fetchNotes(projectId)
      .then(setNotes)
      .catch(() => setNotes([]));
  }

  async function handleUpload(fileList) {
    setUploading(true);
    setUploadError(null);
    try {
      setNotes(await uploadNotes(projectId, fileList));
    } catch (err) {
      if (err instanceof AuthRequiredError) return toLogin();
      setUploadError(err.message || "업로드에 실패했어요.");
    } finally {
      setUploading(false);
    }
  }

  // Replace the in-progress assistant message (always the last one) as events arrive.
  function updateLive(change) {
    setMessages((prev) => [...prev.slice(0, -1), { ...prev[prev.length - 1], ...change(prev[prev.length - 1]) }]);
  }

  async function handleSend(text) {
    if (!sessionId || busy) return false;
    setError(null);
    setSidebarOpen(false);
    const before = messages;
    setMessages([
      ...before,
      { role: "user", content: text },
      { role: "assistant", content: "", status: "생각하고 있어요", streaming: true },
    ]);
    setBusy(true);
    try {
      const final = await sendMessageStream(sessionId, projectId, text, (event) => {
        if (event.type === "status") updateLive(() => ({ status: event.text }));
        if (event.type === "delta") updateLive((m) => ({ content: m.content + event.text }));
      });
      setMessages(final);
      refreshProgress();
      return true;
    } catch (err) {
      // The server did not save this message, so take it back off the screen too.
      setMessages(before);
      if (err instanceof AuthRequiredError) {
        toLogin();
        return false;
      }
      setError(err.message || "응답을 가져오지 못했어요. 잠시 후 다시 보내주세요.");
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function handleAnswerQuiz(quizId, choice) {
    try {
      const card = await answerQuiz(sessionId, projectId, quizId, choice);
      setMessages((prev) => prev.map((m) => (m.quiz?.id === quizId ? { ...m, quiz: card } : m)));
      refreshProgress();
    } catch (err) {
      if (err instanceof AuthRequiredError) return toLogin();
      throw err;
    }
  }

  async function handleReset() {
    if (!sessionId || busy) return;
    // Start a new conversation; the old one stays saved on the server.
    const data = await createSession(projectId, { fresh: true });
    setSessionId(data.session_id);
    setMessages(data.messages);
    setError(null);
    setSidebarOpen(false);
  }

  return (
    <div className="app-shell">
      <Sidebar
        weakTopics={weakTopics}
        reviewTopics={reviewTopics}
        notes={notes ?? []}
        onReset={handleReset}
        onUpload={handleUpload}
        onPractice={(topic) => handleSend(`${topic} 퀴즈 내줘`)}
        uploading={uploading}
        uploadError={uploadError}
        busy={busy}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />
      <main className="main-panel">
        <header className="app-topbar">
          <button
            type="button"
            className="sidebar-toggle"
            aria-label="노트와 약점 주제 열기"
            onClick={() => setSidebarOpen(true)}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M4 6h16M4 12h16M4 18h16" strokeLinecap="round" />
            </svg>
          </button>
          <Link to="/app" className="topbar-logo" aria-label="과목 목록으로">
            <Logo size={26} />
          </Link>
          <p className="topbar-subtitle">{projectName || "학습 파트너"}</p>
        </header>
        {error && (
          <div className="error-banner" role="alert">
            {error}
          </div>
        )}
        {notes !== null && (
          <ChatWindow
            messages={messages}
            busy={busy}
            onSend={handleSend}
            onAnswerQuiz={handleAnswerQuiz}
            hasNotes={notes.length > 0}
            onUpload={handleUpload}
            uploading={uploading}
          />
        )}
      </main>
    </div>
  );
}
