const BASE = "/api";

export class AuthRequiredError extends Error {}

async function failure(res, path) {
  const data = await res.json().catch(() => null);
  const message = data?.detail || `${path} failed: ${res.status}`;
  // A study request without a valid login cookie sends the user back to the login page.
  if (res.status === 401 && !path.startsWith("/auth/")) {
    return new AuthRequiredError(message);
  }
  return new Error(message);
}

async function request(path, options) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) throw await failure(res, path);
  return res.json();
}

export function fetchMe() {
  return request("/auth/me", { method: "GET" });
}

export function fetchAuthConfig() {
  return request("/auth/config", { method: "GET" });
}

export function login(username, password) {
  return request("/auth/login", { method: "POST", body: JSON.stringify({ username, password }) });
}

export function signup(username, password, signupCode) {
  return request("/auth/signup", {
    method: "POST",
    body: JSON.stringify({ username, password, signup_code: signupCode || null }),
  });
}

export function logout() {
  return request("/auth/logout", { method: "POST" });
}

export function createProject(name) {
  return request("/projects", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export function fetchProjects() {
  return request("/projects", { method: "GET" });
}

function sessionKey(projectId) {
  return `recap:session:${projectId}`;
}

function rememberedSession(projectId) {
  try {
    return localStorage.getItem(sessionKey(projectId));
  } catch {
    return null;
  }
}

export function rememberSession(projectId, sessionId) {
  try {
    if (sessionId) localStorage.setItem(sessionKey(projectId), sessionId);
    else localStorage.removeItem(sessionKey(projectId));
  } catch {
    // Private mode or blocked storage: the chat still works, it just won't resume.
  }
}

export async function createSession(projectId, { fresh = false } = {}) {
  const data = await request("/session", {
    method: "POST",
    body: JSON.stringify({ project_id: projectId, resume_session_id: fresh ? null : rememberedSession(projectId) }),
  });
  rememberSession(projectId, data.session_id);
  return data;
}

export function sendMessage(sessionId, projectId, message) {
  return request("/chat", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId, project_id: projectId, message }),
  });
}

export function resetConversation(sessionId, projectId) {
  return request("/reset", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId, project_id: projectId }),
  });
}

export function fetchWeakTopics(projectId) {
  return request(`/weak-topics?project_id=${encodeURIComponent(projectId)}`, { method: "GET" });
}

export function fetchNotes(projectId) {
  return request(`/notes?project_id=${encodeURIComponent(projectId)}`, { method: "GET" });
}

export async function uploadNotes(projectId, fileList) {
  const body = new FormData();
  body.append("project_id", projectId);
  for (const file of fileList) {
    body.append("files", file);
  }
  const res = await fetch(`${BASE}/notes`, { method: "POST", body });
  if (!res.ok) throw await failure(res, "/notes");
  return res.json();
}

export function answerQuiz(sessionId, projectId, quizId, choice) {
  return request("/quiz/answer", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId, project_id: projectId, quiz_id: quizId, choice }),
  });
}

export function fetchReview(projectId) {
  return request(`/review?project_id=${encodeURIComponent(projectId)}`, { method: "GET" });
}

export function createSampleProject() {
  return request("/projects/sample", { method: "POST" });
}

// Streams one chat turn. onEvent gets {type: "status"|"delta", text}; resolves with the
// final screen messages, or throws with the server's message if the turn failed.
export async function sendMessageStream(sessionId, projectId, message, onEvent) {
  const res = await fetch(`${BASE}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, project_id: projectId, message }),
  });
  if (!res.ok) throw await failure(res, "/chat/stream");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop();
    for (const part of parts) {
      if (!part.startsWith("data: ")) continue;
      const event = JSON.parse(part.slice(6));
      if (event.type === "done") return event.messages;
      if (event.type === "error") throw new Error(event.detail);
      onEvent(event);
    }
  }
  throw new Error("응답이 중간에 끊겼어요. 다시 보내주세요.");
}
