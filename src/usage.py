"""Per-user chat counter, so one account can't use up the shared OpenAI budget."""

import hashlib
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
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS guest_starts (
            ip_hash TEXT NOT NULL,
            started_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    return conn


def _hash_ip(ip: str) -> str:
    # Only needed for counting, so the address itself is never stored.
    return hashlib.sha256(ip.encode()).hexdigest()


def guests_today(ip: str) -> int:
    conn = get_connection()
    count = conn.execute(
        "SELECT COUNT(*) FROM guest_starts WHERE ip_hash = ? AND started_at > datetime('now', '-1 day')",
        (_hash_ip(ip),),
    ).fetchone()[0]
    conn.close()
    return count


def record_guest(ip: str) -> None:
    conn = get_connection()
    with conn:
        conn.execute("INSERT INTO guest_starts (ip_hash) VALUES (?)", (_hash_ip(ip),))
        conn.execute("DELETE FROM guest_starts WHERE started_at < datetime('now', '-1 day')")
    conn.close()


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
