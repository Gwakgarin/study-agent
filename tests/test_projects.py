import pytest

from src import projects


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(projects, "DB_PATH", tmp_path / "tracker.db")
    monkeypatch.setattr(projects, "PROJECTS_ROOT", tmp_path / "projects")


def test_create_project_returns_id_and_name():
    project = projects.create_project("생물학", "u1")

    assert project["id"]
    assert project["name"] == "생물학"
    assert project["created_at"]


def test_list_projects_empty_when_none_created():
    assert projects.list_projects("u1") == []


def test_list_projects_returns_created_projects_in_order():
    first = projects.create_project("생물학", "u1")
    second = projects.create_project("화학", "u1")

    result = projects.list_projects("u1")

    assert [p["id"] for p in result] == [first["id"], second["id"]]


def test_list_projects_only_returns_that_users_projects():
    mine = projects.create_project("생물학", "u1")
    projects.create_project("화학", "u2")

    assert [p["id"] for p in projects.list_projects("u1")] == [mine["id"]]


def test_get_project_returns_none_when_missing():
    assert projects.get_project("does-not-exist") is None


def test_get_project_returns_matching_project():
    created = projects.create_project("생물학", "u1")

    assert projects.get_project(created["id"]) == created


def test_old_database_without_owner_column_is_migrated():
    import sqlite3

    conn = sqlite3.connect(projects.DB_PATH)
    conn.execute(
        "CREATE TABLE projects (id TEXT PRIMARY KEY, name TEXT NOT NULL, "
        "created_at TEXT NOT NULL DEFAULT (datetime('now')))"
    )
    conn.execute("INSERT INTO projects (id, name) VALUES ('old', '한국사')")
    conn.commit()
    conn.close()

    assert projects.get_project("old")["user_id"] is None
    assert projects.claim_unowned_projects("u1") == 1
    assert [p["id"] for p in projects.list_projects("u1")] == ["old"]


def test_notes_dir_and_index_dir_are_scoped_per_project():
    notes = projects.notes_dir("abc")
    index = projects.index_dir("abc")

    assert notes == projects.PROJECTS_ROOT / "abc" / "notes"
    assert index == projects.PROJECTS_ROOT / "abc" / "index"
