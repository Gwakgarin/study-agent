import json

import faiss
import numpy as np
import pytest

from src import projects, search


@pytest.fixture(autouse=True)
def reset_search_cache():
    search._cache.clear()
    yield
    search._cache.clear()


def _build_fake_index(project_id, vectors, metadata):
    index_dir = projects.index_dir(project_id)
    index_dir.mkdir(parents=True)
    arr = np.array(vectors, dtype="float32")
    faiss.normalize_L2(arr)
    index = faiss.IndexFlatIP(arr.shape[1])
    index.add(arr)
    faiss.write_index(index, str(index_dir / "notes.index"))
    (index_dir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False))


def test_search_notes_returns_closest_match_first(tmp_path, monkeypatch, fake_openai_factory):
    monkeypatch.setattr(projects, "PROJECTS_ROOT", tmp_path / "projects")
    metadata = [
        {"source": "a.md", "chunk_index": 0, "text": "faiss는 유사도 검색 라이브러리다"},
        {"source": "b.md", "chunk_index": 0, "text": "rag는 검색 증강 생성이다"},
    ]
    _build_fake_index("p1", [[1.0, 0.0], [0.0, 1.0]], metadata)

    fake_client = fake_openai_factory(vectors_by_text={"faiss가 뭐야": [1.0, 0.0]})
    monkeypatch.setattr(search, "get_client", lambda: fake_client)

    results = search.search_notes("p1", "faiss가 뭐야", k=2)

    assert len(results) == 2
    assert results[0]["source"] == "a.md"
    assert results[0]["score"] == pytest.approx(1.0)
    assert results[1]["source"] == "b.md"


def test_search_notes_respects_k(tmp_path, monkeypatch, fake_openai_factory):
    monkeypatch.setattr(projects, "PROJECTS_ROOT", tmp_path / "projects")
    metadata = [
        {"source": f"{i}.md", "chunk_index": 0, "text": f"note {i}"} for i in range(3)
    ]
    _build_fake_index("p1", [[1.0, 0.0], [0.9, 0.1], [0.0, 1.0]], metadata)

    fake_client = fake_openai_factory(vectors_by_text={"q": [1.0, 0.0]})
    monkeypatch.setattr(search, "get_client", lambda: fake_client)

    results = search.search_notes("p1", "q", k=1)

    assert len(results) == 1


def test_search_notes_raises_when_index_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(projects, "PROJECTS_ROOT", tmp_path / "projects")

    with pytest.raises(FileNotFoundError):
        search.search_notes("does-not-exist", "anything")


def test_search_notes_is_isolated_per_project(tmp_path, monkeypatch, fake_openai_factory):
    monkeypatch.setattr(projects, "PROJECTS_ROOT", tmp_path / "projects")
    _build_fake_index("p1", [[1.0, 0.0]], [{"source": "p1.md", "chunk_index": 0, "text": "p1 note"}])
    _build_fake_index("p2", [[1.0, 0.0]], [{"source": "p2.md", "chunk_index": 0, "text": "p2 note"}])

    fake_client = fake_openai_factory(vectors_by_text={"q": [1.0, 0.0]})
    monkeypatch.setattr(search, "get_client", lambda: fake_client)

    assert search.search_notes("p1", "q")[0]["source"] == "p1.md"
    assert search.search_notes("p2", "q")[0]["source"] == "p2.md"


def test_invalidate_forces_reload(tmp_path, monkeypatch, fake_openai_factory):
    monkeypatch.setattr(projects, "PROJECTS_ROOT", tmp_path / "projects")
    _build_fake_index("p1", [[1.0, 0.0]], [{"source": "old.md", "chunk_index": 0, "text": "old"}])

    fake_client = fake_openai_factory(vectors_by_text={"q": [1.0, 0.0]})
    monkeypatch.setattr(search, "get_client", lambda: fake_client)

    search.search_notes("p1", "q")
    assert "p1" in search._cache

    search.invalidate("p1")

    assert "p1" not in search._cache
