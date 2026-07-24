"""Query the FAISS index built by ingest.py."""

import json
from pathlib import Path

import faiss
import numpy as np

from src.ingest import EMBEDDING_MODEL, INDEX_DIR, get_client

_index = None
_metadata: list[dict] | None = None


def _load_index():
    global _index, _metadata
    if _index is None:
        index_path = INDEX_DIR / "notes.index"
        metadata_path = INDEX_DIR / "metadata.json"
        if not index_path.exists():
            raise FileNotFoundError(
                f"No index found at {index_path} — run `python -m src.ingest` first."
            )
        _index = faiss.read_index(str(index_path))
        _metadata = json.loads(metadata_path.read_text())
    return _index, _metadata


def search_notes(query: str, k: int = 5) -> list[dict]:
    index, metadata = _load_index()

    response = get_client().embeddings.create(model=EMBEDDING_MODEL, input=[query])
    vector = np.array([response.data[0].embedding], dtype="float32")
    faiss.normalize_L2(vector)

    scores, indices = index.search(vector, k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx == -1:
            continue
        entry = metadata[idx]
        results.append(
            {
                "source": entry["source"],
                "text": entry["text"],
                "score": float(score),
            }
        )
    return results
