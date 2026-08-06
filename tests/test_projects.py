import pytest

from src import projects


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(projects, "DB_PATH", tmp_path / "tracker.db")
    monkeypatch.setattr(projects, "PROJECTS_ROOT", tmp_path / "projects")


def test_create_project_returns_id_and_name():
    project = projects.create_project("생물학")

    assert project["id"]
    assert project["name"] == "생물학"
    assert project["created_at"]


def test_list_projects_empty_when_none_created():
    assert projects.list_projects() == []


def test_list_projects_returns_created_projects_in_order():
    first = projects.create_project("생물학")
    second = projects.create_project("화학")

    result = projects.list_projects()

    assert [p["id"] for p in result] == [first["id"], second["id"]]


def test_get_project_returns_none_when_missing():
    assert projects.get_project("does-not-exist") is None


def test_get_project_returns_matching_project():
    created = projects.create_project("생물학")

    assert projects.get_project(created["id"]) == created


def test_notes_dir_and_index_dir_are_scoped_per_project():
    notes = projects.notes_dir("abc")
    index = projects.index_dir("abc")

    assert notes == projects.PROJECTS_ROOT / "abc" / "notes"
    assert index == projects.PROJECTS_ROOT / "abc" / "index"
