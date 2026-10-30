import json
import zipfile

import faiss
import numpy as np
import pytest

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
    assert metadata == [{"source": "a.md", "chunk_index": 0, "section": "", "text": "first note content"}]

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


def test_build_index_raises_when_notes_have_no_readable_text(tmp_path, monkeypatch):
    monkeypatch.setattr(projects, "PROJECTS_ROOT", tmp_path / "projects")
    notes_path = projects.notes_dir("p1")
    notes_path.mkdir(parents=True)
    (notes_path / "blank.md").write_text("   \n\n", encoding="utf-8")

    with pytest.raises(SystemExit, match="읽을 수 있는 글자"):
        ingest.build_index("p1")


def test_build_index_indexes_docx_notes(tmp_path, monkeypatch, fake_openai_factory):
    monkeypatch.setattr(projects, "PROJECTS_ROOT", tmp_path / "projects")
    notes_path = projects.notes_dir("p1")
    notes_path.mkdir(parents=True)
    _write_docx(notes_path / "lecture.docx", [("Heading1", "정규화"), (None, "이상 현상을 줄이는 과정")])
    monkeypatch.setattr(ingest, "get_client", lambda: fake_openai_factory())

    ingest.build_index("p1")

    metadata = json.loads((projects.index_dir("p1") / "metadata.json").read_text())
    assert metadata == [
        {"source": "lecture.docx", "chunk_index": 0, "section": "정규화", "text": "이상 현상을 줄이는 과정"}
    ]


def test_build_index_reuses_embeddings_for_unchanged_chunks(tmp_path, monkeypatch, fake_openai_factory):
    monkeypatch.setattr(projects, "PROJECTS_ROOT", tmp_path / "projects")
    notes_path = projects.notes_dir("p1")
    notes_path.mkdir(parents=True)
    (notes_path / "a.md").write_text("## A\nfirst", encoding="utf-8")
    client = fake_openai_factory()
    monkeypatch.setattr(ingest, "get_client", lambda: client)

    ingest.build_index("p1")
    (notes_path / "b.md").write_text("## B\nsecond", encoding="utf-8")
    ingest.build_index("p1")

    # a.md was embedded once; the second build only paid for b.md.
    assert client.embeddings.calls == [["A\nfirst"], ["B\nsecond"]]
    index = faiss.read_index(str(projects.index_dir("p1") / "notes.index"))
    assert index.ntotal == 2


def test_build_index_drops_embeddings_of_deleted_notes_from_the_cache(tmp_path, monkeypatch, fake_openai_factory):
    monkeypatch.setattr(projects, "PROJECTS_ROOT", tmp_path / "projects")
    notes_path = projects.notes_dir("p1")
    notes_path.mkdir(parents=True)
    (notes_path / "a.md").write_text("first", encoding="utf-8")
    (notes_path / "b.md").write_text("second", encoding="utf-8")
    monkeypatch.setattr(ingest, "get_client", lambda: fake_openai_factory())
    ingest.build_index("p1")

    (notes_path / "b.md").unlink()
    ingest.build_index("p1")

    with np.load(projects.index_dir("p1") / "embeddings.npz") as cache:
        assert len(cache["keys"]) == 1


def test_embed_chunks_sends_large_inputs_in_batches(monkeypatch, fake_openai_factory):
    client = fake_openai_factory()
    monkeypatch.setattr(ingest, "get_client", lambda: client)
    monkeypatch.setattr(ingest, "EMBED_BATCH", 2)

    vectors = ingest.embed_chunks(["a", "b", "c", "d", "e"])

    assert [len(call) for call in client.embeddings.calls] == [2, 2, 1]
    assert len(vectors) == 5


def _write_docx(path, paragraphs):
    """A minimal .docx: (style, text) paragraphs in word/document.xml."""
    ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    body = ""
    for style, text in paragraphs:
        props = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
        body += f"<w:p>{props}<w:r><w:t>{text}</w:t></w:r></w:p>"
    xml = f'<?xml version="1.0"?><w:document xmlns:w="{ns}"><w:body>{body}</w:body></w:document>'
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", xml)


def test_load_text_reads_docx_headings_as_markdown(tmp_path):
    path = tmp_path / "n.docx"
    _write_docx(path, [("Heading1", "제목"), ("Heading2", "소제목"), (None, "본문"), (None, "")])

    assert ingest.load_text(path) == "# 제목\n## 소제목\n본문"


def test_load_text_rejects_docx_that_expands_too_large(tmp_path, monkeypatch):
    path = tmp_path / "n.docx"
    _write_docx(path, [(None, "x" * 100)])
    monkeypatch.setattr(ingest, "MAX_DOCX_XML_BYTES", 10)

    with pytest.raises(ValueError):
        ingest.load_text(path)


def test_chunk_document_follows_headings_and_records_the_heading_path():
    text = "# 책\n## 1장\n본문 하나\n### 1.1절\n본문 둘\n## 2장\n본문 셋"

    assert ingest.chunk_document(text) == [
        {"section": "책 > 1장", "text": "본문 하나"},
        {"section": "책 > 1장 > 1.1절", "text": "본문 둘"},
        {"section": "책 > 2장", "text": "본문 셋"},
    ]


def test_chunk_document_ignores_hash_lines_inside_code_fences():
    text = "## 스크립트\n```bash\n# 이건 주석\nls\n```"

    chunks = ingest.chunk_document(text)

    assert [c["section"] for c in chunks] == ["스크립트"]
    assert "# 이건 주석" in chunks[0]["text"]


def test_chunk_document_keeps_a_trailing_hash_in_a_heading_title():
    assert ingest.chunk_document("## C#\n문법")[0]["section"] == "C#"


def test_chunk_document_text_without_headings_has_empty_section():
    assert ingest.chunk_document("그냥 메모") == [{"section": "", "text": "그냥 메모"}]


def test_chunk_document_splits_long_sections_on_line_boundaries():
    text = "## 긴 절\n" + "\n".join(f"문장 {i}번입니다." for i in range(10))

    chunks = ingest.chunk_document(text, chunk_size=40, overlap=0)

    assert len(chunks) > 1
    assert all(c["section"] == "긴 절" and len(c["text"]) <= 40 for c in chunks)
    # no sentence is cut in half
    assert "\n".join(c["text"] for c in chunks) == "\n".join(f"문장 {i}번입니다." for i in range(10))


def test_chunk_document_windows_a_single_line_longer_than_chunk_size():
    chunks = ingest.chunk_document("a" * 25, chunk_size=10, overlap=0)

    assert [len(c["text"]) for c in chunks] == [10, 10, 5]


def test_embedding_text_prefixes_the_heading_path():
    assert ingest.embedding_text({"section": "책 > 1장", "text": "본문"}) == "책 > 1장\n본문"
    assert ingest.embedding_text({"section": "", "text": "본문"}) == "본문"
