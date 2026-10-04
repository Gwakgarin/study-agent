"""Per-user chat counter, so one account can't use up the shared OpenAI budget."""

import sqlite3

from src.config import settings

DB_PATH = settings.db_path


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_usage (
            user_id TEXT NOT NULL,
            used_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    return conn


def chats_in_last_hour(user_id: str) -> int:
    conn = get_connection()
    count = conn.execute(
        "SELECT COUNT(*) FROM chat_usage WHERE user_id = ? AND used_at > datetime('now', '-1 hour')",
        (user_id,),
    ).fetchone()[0]
    conn.close()
    return count


def record_chat(user_id: str) -> None:
    conn = get_connection()
    with conn:
        conn.execute("INSERT INTO chat_usage (user_id) VALUES (?)", (user_id,))
        # Rows older than a day can never count again.
        conn.execute("DELETE FROM chat_usage WHERE used_at < datetime('now', '-1 day')")
    conn.close()
