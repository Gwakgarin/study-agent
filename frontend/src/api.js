const BASE = "/api";

async function request(path, options) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    throw new Error(`${path} failed: ${res.status}`);
  }
  return res.json();
}

export function createSession() {
  return request("/session", { method: "POST" });
}

export function sendMessage(sessionId, message) {
  return request("/chat", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId, message }),
  });
}

export function resetConversation(sessionId) {
  return request("/reset", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId }),
  });
}

export function fetchWeakTopics() {
  return request("/weak-topics", { method: "GET" });
}

export function fetchNotes() {
  return request("/notes", { method: "GET" });
}

export async function uploadNotes(fileList) {
  const body = new FormData();
  for (const file of fileList) {
    body.append("files", file);
  }
  const res = await fetch(`${BASE}/notes`, { method: "POST", body });
  if (!res.ok) {
    const data = await res.json().catch(() => null);
    throw new Error(data?.detail || `notes upload failed: ${res.status}`);
  }
  return res.json();
}
