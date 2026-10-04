import pytest
from fastapi.testclient import TestClient

import server
from src import auth, projects, sessions, usage


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    db_path = tmp_path / "study-agent.db"
    for module in (sessions, projects, auth, usage):
        monkeypatch.setattr(module, "DB_PATH", db_path)
    monkeypatch.setattr(projects, "PROJECTS_ROOT", tmp_path / "projects")


def _signup(client, username="alice", password="password1", **extra):
    return client.post("/api/auth/signup", json={"username": username, "password": password, **extra})


def test_password_hash_is_salted_and_verifiable():
    first = auth.hash_password("password1")
    second = auth.hash_password("password1")

    assert first != second
    assert "password1" not in first
    assert auth.verify_password("password1", first)
    assert not auth.verify_password("password2", first)
    assert not auth.verify_password("password1", "garbage")


def test_login_token_is_not_stored_in_plain_text(tmp_path):
    user = auth.create_user("alice", "password1")
    token = auth.create_login(user["id"])

    conn = auth.get_connection()
    stored = [row[0] for row in conn.execute("SELECT token_hash FROM logins")]
    conn.close()

    assert token not in stored
    assert auth.user_for_token(token)["username"] == "alice"


def test_api_requires_login():
    client = TestClient(server.app)

    assert client.get("/api/projects").status_code == 401
    assert client.get("/api/auth/me").status_code == 401


def test_signup_logs_in_and_me_returns_user():
    client = TestClient(server.app)

    res = _signup(client)

    assert res.status_code == 200
    assert client.get("/api/auth/me").json()["username"] == "alice"


@pytest.mark.parametrize(
    "username, password",
    [("ab", "password1"), ("has space", "password1"), ("한글아이디", "password1"), ("alice", "short")],
)
def test_signup_rejects_bad_input(username, password):
    res = _signup(TestClient(server.app), username, password)

    assert res.status_code == 400


def test_signup_rejects_duplicate_username_case_insensitively():
    _signup(TestClient(server.app), "alice")

    res = _signup(TestClient(server.app), "ALICE")

    assert res.status_code == 400


def test_signup_code_is_enforced_when_configured(monkeypatch):
    monkeypatch.setattr(server.settings, "signup_code", "letmein")
    client = TestClient(server.app)

    assert client.get("/api/auth/config").json() == {"signup_code_required": True}
    assert _signup(client).status_code == 403
    assert _signup(client, signup_code="wrong").status_code == 403
    assert _signup(client, signup_code="letmein").status_code == 200


def test_login_with_wrong_password_fails_and_right_one_works():
    _signup(TestClient(server.app))
    client = TestClient(server.app)

    assert client.post("/api/auth/login", json={"username": "alice", "password": "nope"}).status_code == 401
    assert client.post("/api/auth/login", json={"username": "ghost", "password": "password1"}).status_code == 401
    assert client.post("/api/auth/login", json={"username": "alice", "password": "password1"}).status_code == 200
    assert client.get("/api/auth/me").status_code == 200


def test_logout_ends_the_session():
    client = TestClient(server.app)
    _signup(client)

    client.post("/api/auth/logout")

    assert client.get("/api/auth/me").status_code == 401


def test_users_never_see_each_others_projects():
    alice, bob = TestClient(server.app), TestClient(server.app)
    _signup(alice, "alice")
    _signup(bob, "bob")
    project_id = alice.post("/api/projects", json={"name": "SQLD"}).json()["id"]

    assert bob.get("/api/projects").json() == []
    assert bob.get("/api/notes", params={"project_id": project_id}).status_code == 404
    assert bob.get("/api/weak-topics", params={"project_id": project_id}).status_code == 404
    assert bob.post("/api/session", json={"project_id": project_id}).status_code == 404
    upload = bob.post(
        "/api/notes", data={"project_id": project_id}, files=[("files", ("x.txt", b"hi", "text/plain"))]
    )
    assert upload.status_code == 404
    assert not projects.notes_dir(project_id).exists()


def test_session_cannot_be_reused_under_another_project(monkeypatch):
    monkeypatch.setattr(server, "run_turn", lambda messages, project_id: messages)
    client = TestClient(server.app)
    _signup(client)
    first = client.post("/api/projects", json={"name": "A"}).json()["id"]
    second = client.post("/api/projects", json={"name": "B"}).json()["id"]
    session_id = client.post("/api/session", json={"project_id": first}).json()["session_id"]

    res = client.post("/api/chat", json={"session_id": session_id, "project_id": second, "message": "hi"})

    assert res.status_code == 404


def test_chat_is_rate_limited_per_user(monkeypatch):
    monkeypatch.setattr(server.settings, "chat_limit_per_hour", 2)

    def reply(messages, project_id):
        messages.append({"role": "assistant", "content": "ok"})
        return messages

    monkeypatch.setattr(server, "run_turn", reply)
    client = TestClient(server.app)
    _signup(client)
    project_id = client.post("/api/projects", json={"name": "A"}).json()["id"]
    body = {"session_id": "s1", "project_id": project_id, "message": "hi"}

    assert client.post("/api/chat", json=body).status_code == 200
    assert client.post("/api/chat", json=body).status_code == 200
    assert client.post("/api/chat", json=body).status_code == 429

    other = TestClient(server.app)
    _signup(other, "bob")
    other_project = other.post("/api/projects", json={"name": "B"}).json()["id"]
    res = other.post("/api/chat", json={"session_id": "s2", "project_id": other_project, "message": "hi"})
    assert res.status_code == 200


def test_upload_strips_directories_from_filenames(monkeypatch, fake_openai_factory):
    from src import ingest

    monkeypatch.setattr(ingest, "get_client", lambda: fake_openai_factory())
    client = TestClient(server.app)
    _signup(client)
    project_id = client.post("/api/projects", json={"name": "A"}).json()["id"]

    res = client.post(
        "/api/notes",
        data={"project_id": project_id},
        files=[("files", ("../../escape.txt", b"hello", "text/plain"))],
    )

    assert res.status_code == 200
    assert (projects.notes_dir(project_id) / "escape.txt").exists()
    assert not (projects.PROJECTS_ROOT / "escape.txt").exists()


def test_upload_rejects_files_over_the_size_limit(monkeypatch):
    monkeypatch.setattr(server.settings, "max_upload_mb", 1)
    client = TestClient(server.app)
    _signup(client)
    project_id = client.post("/api/projects", json={"name": "A"}).json()["id"]

    res = client.post(
        "/api/notes",
        data={"project_id": project_id},
        files=[("files", ("big.txt", b"x" * (1024 * 1024 + 1), "text/plain"))],
    )

    assert res.status_code == 400
    assert not projects.notes_dir(project_id).exists()


def test_upload_rejects_too_many_notes(monkeypatch):
    monkeypatch.setattr(server.settings, "max_notes_per_project", 1)
    client = TestClient(server.app)
    _signup(client)
    project_id = client.post("/api/projects", json={"name": "A"}).json()["id"]

    res = client.post(
        "/api/notes",
        data={"project_id": project_id},
        files=[("files", ("a.txt", b"a", "text/plain")), ("files", ("b.txt", b"b", "text/plain"))],
    )

    assert res.status_code == 400
