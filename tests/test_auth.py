import pytest
from fastapi.testclient import TestClient

import server
from src import auth, projects, quizzes, sessions, tracker, usage


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    db_path = tmp_path / "study-agent.db"
    for module in (sessions, projects, auth, usage, quizzes, tracker):
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


def test_sample_project_is_created_once_with_indexed_notes(monkeypatch, fake_openai_factory):
    from src import ingest

    monkeypatch.setattr(ingest, "get_client", lambda: fake_openai_factory())
    client = TestClient(server.app)
    _signup(client)

    first = client.post("/api/projects/sample").json()
    again = client.post("/api/projects/sample").json()

    assert first["id"] == again["id"]
    listed = client.get("/api/projects").json()
    assert len(listed) == 1
    assert listed[0]["notes"] == 6
    assert listed[0]["attempts"] == 0 and listed[0]["accuracy"] is None


def test_review_lists_due_topics_for_owner_only(monkeypatch):
    alice, bob = TestClient(server.app), TestClient(server.app)
    _signup(alice, "alice")
    _signup(bob, "bob")
    project_id = alice.post("/api/projects", json={"name": "A"}).json()["id"]
    tracker.record_answer(project_id, "조인", False)
    conn = tracker.get_connection()
    with conn:
        conn.execute("UPDATE schedule SET next_review_at = datetime('now', '-1 day')")
    conn.close()

    assert [t["topic"] for t in alice.get("/api/review", params={"project_id": project_id}).json()] == ["조인"]
    assert bob.get("/api/review", params={"project_id": project_id}).status_code == 404
    card = alice.get("/api/projects").json()[0]
    assert card["attempts"] == 1 and card["accuracy"] == 0 and card["due"] == 1


def test_guest_gets_an_account_without_signing_up():
    client = TestClient(server.app)

    guest = client.post("/api/auth/guest").json()
    me = client.get("/api/auth/me").json()

    assert guest["is_guest"] is True
    assert me["id"] == guest["id"]
    assert client.post("/api/projects", json={"name": "SQLD"}).status_code == 200


def test_guest_endpoint_reuses_existing_login():
    client = TestClient(server.app)
    first = client.post("/api/auth/guest").json()

    assert client.post("/api/auth/guest").json()["id"] == first["id"]


def test_guests_are_limited_per_address(monkeypatch):
    monkeypatch.setattr(server.settings, "guest_limit_per_ip_per_day", 2)
    here = {"fly-client-ip": "203.0.113.7"}

    # Clearing cookies (a fresh client) used to mean an endless supply of guests.
    for _ in range(2):
        assert TestClient(server.app).post("/api/auth/guest", headers=here).status_code == 200
    blocked = TestClient(server.app).post("/api/auth/guest", headers=here)

    assert blocked.status_code == 429
    assert "가입" in blocked.json()["detail"]
    elsewhere = {"fly-client-ip": "198.51.100.2"}
    assert TestClient(server.app).post("/api/auth/guest", headers=elsewhere).status_code == 200


def test_returning_guest_is_not_counted_again(monkeypatch):
    monkeypatch.setattr(server.settings, "guest_limit_per_ip_per_day", 1)
    client = TestClient(server.app)
    here = {"fly-client-ip": "203.0.113.7"}

    client.post("/api/auth/guest", headers=here)

    assert client.post("/api/auth/guest", headers=here).status_code == 200


def test_guest_cannot_upload_notes():
    client = TestClient(server.app)
    client.post("/api/auth/guest")
    project = client.post("/api/projects", json={"name": "SQLD"}).json()

    res = client.post(
        "/api/notes",
        data={"project_id": project["id"]},
        files={"files": ("a.md", b"# A\n\nbody", "text/markdown")},
    )

    assert res.status_code == 403


def test_saving_a_guest_keeps_their_subjects():
    client = TestClient(server.app)
    guest = client.post("/api/auth/guest").json()
    project = client.post("/api/projects", json={"name": "SQLD"}).json()

    saved = client.post("/api/auth/upgrade", json={"username": "alice", "password": "password1"})

    assert saved.status_code == 200
    assert saved.json() == {"id": guest["id"], "username": "alice", "is_guest": False}
    assert [p["id"] for p in client.get("/api/projects").json()] == [project["id"]]

    other = TestClient(server.app)
    assert other.post("/api/auth/login", json={"username": "alice", "password": "password1"}).status_code == 200


def test_guest_cannot_take_a_used_or_reserved_username():
    _signup(TestClient(server.app))
    client = TestClient(server.app)
    client.post("/api/auth/guest")

    taken = client.post("/api/auth/upgrade", json={"username": "alice", "password": "password1"})
    reserved = client.post("/api/auth/upgrade", json={"username": "guest_abc", "password": "password1"})

    assert taken.status_code == 400
    assert reserved.status_code == 400


def test_nobody_can_log_in_to_a_guest_with_a_password():
    client = TestClient(server.app)
    guest = client.post("/api/auth/guest").json()

    res = TestClient(server.app).post("/api/auth/login", json={"username": guest["username"], "password": "!"})

    assert res.status_code == 401


def test_guest_has_a_lower_chat_limit(monkeypatch):
    client = TestClient(server.app)
    guest = client.post("/api/auth/guest").json()
    project = client.post("/api/projects", json={"name": "SQLD"}).json()
    session = client.post("/api/session", json={"project_id": project["id"]}).json()
    monkeypatch.setattr(server.settings, "guest_chat_limit_per_hour", 1)
    usage.record_chat(guest["id"])

    res = client.post(
        "/api/chat",
        json={"session_id": session["session_id"], "project_id": project["id"], "message": "hi"},
    )

    assert res.status_code == 429
    assert "기록을 저장" in res.json()["detail"]
