"""Query the per-project FAISS index built by ingest.py."""

import json

import faiss
import numpy as np

from src.hybrid import BM25, WEIGHTS, rrf
from src.ingest import EMBEDDING_MODEL, embedding_text, get_client
from src.projects import index_dir

_cache: dict[str, tuple] = {}
_bm25_cache: dict[str, tuple] = {}
# How many candidates each ranking contributes before fusion.
POOL = 20


def _bm25(project_id: str, metadata: list[dict]) -> BM25:
    # Keyed on the metadata object itself, so a reloaded or replaced index rebuilds it.
    cached = _bm25_cache.get(project_id)
    if cached is None or cached[0] is not metadata:
        cached = (metadata, BM25([embedding_text(m) for m in metadata]))
        _bm25_cache[project_id] = cached
    return cached[1]


def invalidate(project_id: str) -> None:
    """Drop a project's cached index so the next search reloads it from disk."""
    _cache.pop(project_id, None)
    _bm25_cache.pop(project_id, None)


def _load_index(project_id: str):
    if project_id not in _cache:
        project_index_dir = index_dir(project_id)
        index_path = project_index_dir / "notes.index"
        metadata_path = project_index_dir / "metadata.json"
        if not index_path.exists():
            raise FileNotFoundError(
                f"No index found at {index_path} — upload notes for this project first."
            )
        index = faiss.read_index(str(index_path))
        metadata = json.loads(metadata_path.read_text())
        _cache[project_id] = (index, metadata)
    return _cache[project_id]


def search_notes(project_id: str, query: str, k: int = 5) -> list[dict]:
    index, metadata = _load_index(project_id)

    response = get_client().embeddings.create(model=EMBEDDING_MODEL, input=[query])
    vector = np.array([response.data[0].embedding], dtype="float32")
    faiss.normalize_L2(vector)

    _, dense = index.search(vector, min(max(POOL, k), len(metadata)))
    dense_ranking = [int(i) for i in dense[0] if i != -1]
    fused = rrf([dense_ranking, _bm25(project_id, metadata).rank(query, POOL)], WEIGHTS)[:k]

    results = []
    for idx in fused:
        entry = metadata[idx]
        results.append(
            {
                "source": entry["source"],
                "section": entry.get("section", ""),
                "text": entry["text"],
                # Cosine similarity, as before: callers read it as "how close is this chunk".
                "score": float(index.reconstruct(idx) @ vector[0]),
            }
        )
    return results
