"""SQLite-backed persistence for chat session history, so restarts don't lose in-progress chats."""

import json
import sqlite3

from src.config import settings

DB_PATH = settings.db_path


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            messages TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    return conn


def save_session(session_id: str, messages: list[dict]) -> None:
    conn = get_connection()
    with conn:
        conn.execute(
            """
            INSERT INTO sessions (session_id, messages, updated_at)
            VALUES (?, ?, datetime('now'))
            ON CONFLICT(session_id) DO UPDATE SET
                messages = excluded.messages,
                updated_at = excluded.updated_at
            """,
            (session_id, json.dumps(messages, ensure_ascii=False)),
        )
    conn.close()


def load_session(session_id: str) -> list[dict] | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT messages FROM sessions WHERE session_id = ?", (session_id,)
    ).fetchone()
    conn.close()
    if row is None:
        return None
    return json.loads(row[0])


def delete_session(session_id: str) -> None:
    conn = get_connection()
    with conn:
        conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
    conn.close()
