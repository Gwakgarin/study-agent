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
  if (!res.ok) throw await failure(res, "/notes");
  return res.json();
}
