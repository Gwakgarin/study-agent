"""Load a project's notes, chunk them, embed with OpenAI, and build its FAISS index."""

import hashlib
import json
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import faiss
import numpy as np
from openai import OpenAI
from pypdf import PdfReader

from src.config import settings
from src.projects import index_dir, notes_dir

EMBEDDING_MODEL = settings.embedding_model
CHUNK_SIZE = settings.chunk_size
CHUNK_OVERLAP = settings.chunk_overlap

SUPPORTED_SUFFIXES = (".pdf", ".md", ".txt", ".docx")

# OpenAI accepts up to 2048 inputs per embeddings call; stay well under it.
EMBED_BATCH = 100
# A .docx is a zip: refuse ones that would expand into something absurd.
MAX_DOCX_XML_BYTES = 20 * 1024 * 1024

_client: OpenAI | None = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        if not settings.openai_api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Copy .env.example to .env and add your key."
            )
        _client = OpenAI(
            api_key=settings.openai_api_key,
            timeout=settings.openai_timeout_seconds,
            max_retries=settings.openai_max_retries,
        )
    return _client


_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_DOCX_HEADING = re.compile(r"^heading\s*(\d)$", re.IGNORECASE)


def _docx_to_markdown(path: Path) -> str:
    """Paragraph text from word/document.xml, with Word headings turned into '#' lines."""
    with zipfile.ZipFile(path) as archive:
        info = archive.getinfo("word/document.xml")
        if info.file_size > MAX_DOCX_XML_BYTES:
            raise ValueError("문서가 너무 커서 읽을 수 없어요.")
        root = ET.fromstring(archive.read(info))

    lines = []
    for paragraph in root.iter(f"{_W}p"):
        text = "".join(node.text or "" for node in paragraph.iter(f"{_W}t")).strip()
        if not text:
            continue
        style = paragraph.find(f"{_W}pPr/{_W}pStyle")
        match = _DOCX_HEADING.match(style.get(f"{_W}val", "")) if style is not None else None
        lines.append(f"{'#' * int(match.group(1))} {text}" if match else text)
    return "\n".join(lines)


def load_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if suffix == ".docx":
        return _docx_to_markdown(path)
    return path.read_text(encoding="utf-8")


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return [c.strip() for c in chunks if c.strip()]


_HEADING = re.compile(r"^(#{1,6})\s+(.+?)(?:\s+#+)?\s*$")
_FENCE = re.compile(r"^\s*(```|~~~)")


def _sections(text: str) -> list[tuple[str, str]]:
    """Split a note at its headings into (heading path, body) pairs.

    '#' lines inside code fences are code comments, not headings.
    """
    sections: list[tuple[str, str]] = []
    stack: list[tuple[int, str]] = []
    body: list[str] = []
    in_fence = False

    def flush():
        joined = "\n".join(body).strip()
        if joined:
            sections.append((" > ".join(title for _, title in stack), joined))
        body.clear()

    for line in text.splitlines():
        if _FENCE.match(line):
            in_fence = not in_fence
        heading = None if in_fence else _HEADING.match(line)
        if heading:
            flush()
            level = len(heading.group(1))
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, heading.group(2)))
        else:
            body.append(line)
    flush()
    return sections


def _pack_lines(body: str, chunk_size: int, overlap: int) -> list[str]:
    """Group whole lines up to chunk_size so long sections don't split mid-sentence."""
    pieces: list[str] = []
    current = ""
    for line in body.splitlines():
        if len(line) > chunk_size:
            if current:
                pieces.append(current)
                current = ""
            pieces.extend(chunk_text(line, chunk_size, overlap))
        elif current and len(current) + 1 + len(line) > chunk_size:
            pieces.append(current)
            current = line
        else:
            current = f"{current}\n{line}" if current else line
    if current:
        pieces.append(current)
    return [p.strip() for p in pieces if p.strip()]


def chunk_document(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[dict]:
    """Chunks that follow the note's own structure: [{"section": "Ch1 > NULL", "text": ...}].

    A section that fits in chunk_size stays one chunk, so an answer and the heading that
    explains it are not cut apart. Text without headings still gets sentence-aligned chunks.
    """
    chunks = []
    for section, body in _sections(text):
        pieces = [body] if len(body) <= chunk_size else _pack_lines(body, chunk_size, overlap)
        chunks.extend({"section": section, "text": piece} for piece in pieces)
    return chunks


def embedding_text(entry: dict) -> str:
    """What gets embedded: the heading path gives a short chunk the context its body lacks."""
    section = entry.get("section")
    return f"{section}\n{entry['text']}" if section else entry["text"]


def embed_chunks(chunks: list[str]) -> np.ndarray:
    vectors = []
    for start in range(0, len(chunks), EMBED_BATCH):
        response = get_client().embeddings.create(model=EMBEDDING_MODEL, input=chunks[start : start + EMBED_BATCH])
        vectors.extend(item.embedding for item in response.data)
    return np.array(vectors, dtype="float32")


def _embedding_key(text: str) -> str:
    return hashlib.sha1(f"{EMBEDDING_MODEL}\n{text}".encode()).hexdigest()


def _load_vector_cache(path: Path) -> dict[str, np.ndarray]:
    if not path.exists():
        return {}
    try:
        with np.load(path) as data:
            return dict(zip(data["keys"].tolist(), data["vectors"]))
    except (OSError, ValueError, KeyError):
        return {}


def embed_with_cache(texts: list[str], cache_path: Path) -> np.ndarray:
    """Embed texts, paying only for ones not embedded before (same text + model).

    Adding one note to a subject re-embeds just that note's chunks. The cache is rewritten
    to hold exactly the current texts, so edited or deleted notes don't pile up.
    """
    cached = _load_vector_cache(cache_path)
    keys = [_embedding_key(t) for t in texts]
    missing = list(dict.fromkeys(k for k in keys if k not in cached))
    if missing:
        by_key = dict(zip(keys, texts))
        fresh = embed_chunks([by_key[k] for k in missing])
        faiss.normalize_L2(fresh)
        cached.update(zip(missing, fresh))

    vectors = np.array([cached[k] for k in keys], dtype="float32")
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    unique = list(dict.fromkeys(keys))
    np.savez(cache_path, keys=np.array(unique), vectors=np.array([cached[k] for k in unique], dtype="float32"))
    return vectors


def build_index(project_id: str) -> None:
    notes_path = notes_dir(project_id)
    source_paths = sorted(p for p in notes_path.rglob("*") if p.suffix.lower() in SUPPORTED_SUFFIXES)
    if not source_paths:
        raise SystemExit(f"No notes found in {notes_path} — add PDF/Markdown/text files first.")

    metadata = []
    for path in source_paths:
        for i, chunk in enumerate(chunk_document(load_text(path))):
            metadata.append({"source": path.name, "chunk_index": i, **chunk})
    if not metadata:
        raise SystemExit("노트에서 읽을 수 있는 글자를 찾지 못했어요. 스캔한 이미지 PDF는 아직 지원하지 않아요.")

    index_path = index_dir(project_id)
    vectors = embed_with_cache([embedding_text(m) for m in metadata], index_path / "embeddings.npz")

    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)

    faiss.write_index(index, str(index_path / "notes.index"))
    (index_path / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2)
    )

    print(f"Indexed {len(metadata)} chunks from {len(source_paths)} files.")


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        raise SystemExit("Usage: python -m src.ingest <project_id>")
    build_index(sys.argv[1])
