import json

import faiss
import numpy as np
import pytest

from src import search


@pytest.fixture(autouse=True)
def reset_search_cache():
    """search.py caches the loaded index/metadata at module scope; clear between tests."""
    search._index = None
    search._metadata = None
    yield
    search._index = None
    search._metadata = None


def _build_fake_index(tmp_path, vectors, metadata):
    index_dir = tmp_path / "index"
    index_dir.mkdir()
    arr = np.array(vectors, dtype="float32")
    faiss.normalize_L2(arr)
    index = faiss.IndexFlatIP(arr.shape[1])
    index.add(arr)
    faiss.write_index(index, str(index_dir / "notes.index"))
    (index_dir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False))
    return index_dir


def test_search_notes_returns_closest_match_first(tmp_path, monkeypatch, fake_openai_factory):
    metadata = [
        {"source": "a.md", "chunk_index": 0, "text": "faiss는 유사도 검색 라이브러리다"},
        {"source": "b.md", "chunk_index": 0, "text": "rag는 검색 증강 생성이다"},
    ]
    index_dir = _build_fake_index(tmp_path, [[1.0, 0.0], [0.0, 1.0]], metadata)
    monkeypatch.setattr(search, "INDEX_DIR", index_dir)

    fake_client = fake_openai_factory(vectors_by_text={"faiss가 뭐야": [1.0, 0.0]})
    monkeypatch.setattr(search, "get_client", lambda: fake_client)

    results = search.search_notes("faiss가 뭐야", k=2)

    assert len(results) == 2
    assert results[0]["source"] == "a.md"
    assert results[0]["score"] == pytest.approx(1.0)
    assert results[1]["source"] == "b.md"


def test_search_notes_respects_k(tmp_path, monkeypatch, fake_openai_factory):
    metadata = [
        {"source": f"{i}.md", "chunk_index": 0, "text": f"note {i}"} for i in range(3)
    ]
    index_dir = _build_fake_index(tmp_path, [[1.0, 0.0], [0.9, 0.1], [0.0, 1.0]], metadata)
    monkeypatch.setattr(search, "INDEX_DIR", index_dir)

    fake_client = fake_openai_factory(vectors_by_text={"q": [1.0, 0.0]})
    monkeypatch.setattr(search, "get_client", lambda: fake_client)

    results = search.search_notes("q", k=1)

    assert len(results) == 1


def test_search_notes_raises_when_index_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(search, "INDEX_DIR", tmp_path / "does-not-exist")

    with pytest.raises(FileNotFoundError):
        search.search_notes("anything")
