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
