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

export function createProject(name) {
  return request("/projects", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export function fetchProjects() {
  return request("/projects", { method: "GET" });
}

export function createSession(projectId) {
  return request("/session", {
    method: "POST",
    body: JSON.stringify({ project_id: projectId }),
  });
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
  if (!res.ok) {
    const data = await res.json().catch(() => null);
    throw new Error(data?.detail || `notes upload failed: ${res.status}`);
  }
  return res.json();
}
