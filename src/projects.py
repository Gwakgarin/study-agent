"""SQLite-backed projects (subjects): each belongs to one user and owns its own notes/index directory."""

import sqlite3
import uuid
from pathlib import Path

from src.config import PROJECT_ROOT, settings

DB_PATH = settings.db_path
PROJECTS_ROOT = PROJECT_ROOT / "data" / "projects"


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            user_id TEXT
        )
        """
    )
    # Databases created before accounts existed have no owner column yet.
    columns = {row[1] for row in conn.execute("PRAGMA table_info(projects)")}
    if "user_id" not in columns:
        conn.execute("ALTER TABLE projects ADD COLUMN user_id TEXT")
    return conn


def notes_dir(project_id: str) -> Path:
    return PROJECTS_ROOT / project_id / "notes"


def index_dir(project_id: str) -> Path:
    return PROJECTS_ROOT / project_id / "index"


def _to_dict(row) -> dict:
    return {"id": row[0], "name": row[1], "created_at": row[2], "user_id": row[3]}


def create_project(name: str, user_id: str) -> dict:
    project_id = str(uuid.uuid4())
    conn = get_connection()
    with conn:
        conn.execute(
            "INSERT INTO projects (id, name, user_id) VALUES (?, ?, ?)", (project_id, name, user_id)
        )
    row = conn.execute(
        "SELECT id, name, created_at, user_id FROM projects WHERE id = ?", (project_id,)
    ).fetchone()
    conn.close()
    return _to_dict(row)


def list_projects(user_id: str) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, name, created_at, user_id FROM projects WHERE user_id = ? ORDER BY created_at ASC",
        (user_id,),
    ).fetchall()
    conn.close()
    return [_to_dict(r) for r in rows]


def get_project(project_id: str) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT id, name, created_at, user_id FROM projects WHERE id = ?", (project_id,)
    ).fetchone()
    conn.close()
    return _to_dict(row) if row else None


def claim_unowned_projects(user_id: str) -> int:
    """Give projects created before accounts existed to one user. Returns how many moved."""
    conn = get_connection()
    with conn:
        moved = conn.execute("UPDATE projects SET user_id = ? WHERE user_id IS NULL", (user_id,)).rowcount
    conn.close()
    return moved
