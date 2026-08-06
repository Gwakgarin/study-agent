"""Query the per-project FAISS index built by ingest.py."""

import json

import faiss
import numpy as np

from src.ingest import EMBEDDING_MODEL, get_client
from src.projects import index_dir

_cache: dict[str, tuple] = {}


def invalidate(project_id: str) -> None:
    """Drop a project's cached index so the next search reloads it from disk."""
    _cache.pop(project_id, None)


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
