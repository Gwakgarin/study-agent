"""Load notes from data/notes/, chunk them, embed with OpenAI, and build a FAISS index."""

import json
from pathlib import Path

import faiss
import numpy as np
from openai import OpenAI
from pypdf import PdfReader

from src.config import settings

NOTES_DIR = Path(__file__).resolve().parent.parent / "data" / "notes"
INDEX_DIR = Path(__file__).resolve().parent.parent / "data" / "index"
EMBEDDING_MODEL = settings.embedding_model
CHUNK_SIZE = settings.chunk_size
CHUNK_OVERLAP = settings.chunk_overlap

_client: OpenAI | None = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        if not settings.openai_api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Copy .env.example to .env and add your key."
            )
        _client = OpenAI(api_key=settings.openai_api_key)
    return _client


def load_text(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return path.read_text(encoding="utf-8")


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return [c.strip() for c in chunks if c.strip()]


def embed_chunks(chunks: list[str]) -> np.ndarray:
    response = get_client().embeddings.create(model=EMBEDDING_MODEL, input=chunks)
    vectors = [item.embedding for item in response.data]
    return np.array(vectors, dtype="float32")


def build_index() -> None:
    source_paths = [p for p in NOTES_DIR.rglob("*") if p.suffix.lower() in (".pdf", ".md", ".txt")]
    if not source_paths:
        raise SystemExit(f"No notes found in {NOTES_DIR} — add PDF/Markdown/text files first.")

    metadata = []
    all_chunks = []
    for path in source_paths:
        text = load_text(path)
        for i, chunk in enumerate(chunk_text(text)):
            metadata.append({"source": path.name, "chunk_index": i, "text": chunk})
            all_chunks.append(chunk)

    vectors = embed_chunks(all_chunks)
    faiss.normalize_L2(vectors)

    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)

    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(INDEX_DIR / "notes.index"))
    (INDEX_DIR / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2)
    )

    print(f"Indexed {len(all_chunks)} chunks from {len(source_paths)} files.")


if __name__ == "__main__":
    build_index()
