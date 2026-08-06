import json

import faiss

from src import ingest, projects


def test_chunk_text_splits_with_overlap():
    text = "a" * 10
    chunks = ingest.chunk_text(text, chunk_size=4, overlap=1)
    assert chunks == ["aaaa", "aaaa", "aaaa", "a"]


def test_chunk_text_shorter_than_chunk_size_returns_single_chunk():
    assert ingest.chunk_text("hello", chunk_size=800, overlap=100) == ["hello"]


def test_chunk_text_empty_string_returns_no_chunks():
    assert ingest.chunk_text("") == []


def test_chunk_text_strips_whitespace_only_chunks():
    text = "hello\n\n\n\nworld"
    chunks = ingest.chunk_text(text, chunk_size=5, overlap=0)
    assert all(c == c.strip() and c for c in chunks)


def test_load_text_reads_utf8_text_file(tmp_path):
    path = tmp_path / "note.md"
    path.write_text("한글 노트 내용", encoding="utf-8")
    assert ingest.load_text(path) == "한글 노트 내용"


def test_embed_chunks_calls_client_and_returns_float32_array(monkeypatch, fake_openai_factory):
    fake_client = fake_openai_factory(vectors_by_text={"hello": [1.0, 2.0]})
    monkeypatch.setattr(ingest, "_client", None)
    monkeypatch.setattr(ingest, "get_client", lambda: fake_client)

    vectors = ingest.embed_chunks(["hello"])

    assert vectors.dtype.name == "float32"
    assert vectors.tolist() == [[1.0, 2.0]]
    assert fake_client.embeddings.calls == [["hello"]]


def test_build_index_writes_index_and_metadata(tmp_path, monkeypatch, fake_openai_factory):
    monkeypatch.setattr(projects, "PROJECTS_ROOT", tmp_path / "projects")
    notes_path = projects.notes_dir("p1")
    notes_path.mkdir(parents=True)
    (notes_path / "a.md").write_text("first note content", encoding="utf-8")
    (notes_path / "ignored.png").write_bytes(b"not text")

    fake_client = fake_openai_factory(vectors_by_text={"first note content": [1.0, 0.0]})
    monkeypatch.setattr(ingest, "get_client", lambda: fake_client)

    ingest.build_index("p1")

    index_path = projects.index_dir("p1")
    assert (index_path / "notes.index").exists()
    metadata = json.loads((index_path / "metadata.json").read_text())
    assert metadata == [{"source": "a.md", "chunk_index": 0, "text": "first note content"}]

    index = faiss.read_index(str(index_path / "notes.index"))
    assert index.ntotal == 1


def test_build_index_raises_when_no_notes(tmp_path, monkeypatch):
    monkeypatch.setattr(projects, "PROJECTS_ROOT", tmp_path / "projects")
    projects.notes_dir("empty-project").mkdir(parents=True)

    try:
        ingest.build_index("empty-project")
        assert False, "expected SystemExit"
    except SystemExit as exc:
        assert "No notes found" in str(exc)
