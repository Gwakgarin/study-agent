"""SQLite-backed projects (subjects): each owns its own notes/index directory."""

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
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    return conn


def notes_dir(project_id: str) -> Path:
    return PROJECTS_ROOT / project_id / "notes"


def index_dir(project_id: str) -> Path:
    return PROJECTS_ROOT / project_id / "index"


def create_project(name: str) -> dict:
    project_id = str(uuid.uuid4())
    conn = get_connection()
    with conn:
        conn.execute(
            "INSERT INTO projects (id, name) VALUES (?, ?)", (project_id, name)
        )
    row = conn.execute(
        "SELECT id, name, created_at FROM projects WHERE id = ?", (project_id,)
    ).fetchone()
    conn.close()
    return {"id": row[0], "name": row[1], "created_at": row[2]}


def list_projects() -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, name, created_at FROM projects ORDER BY created_at ASC"
    ).fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1], "created_at": r[2]} for r in rows]


def get_project(project_id: str) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT id, name, created_at FROM projects WHERE id = ?", (project_id,)
    ).fetchone()
    conn.close()
    if row is None:
        return None
    return {"id": row[0], "name": row[1], "created_at": row[2]}
