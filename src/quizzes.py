"""Answers picked on quiz cards. One answer per quiz, so a card can't be re-rolled."""

import sqlite3

from src.config import settings

DB_PATH = settings.db_path


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS quiz_answers (
            quiz_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            choice INTEGER NOT NULL,
            correct INTEGER NOT NULL,
            answered_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    return conn


def save_answer(quiz_id: str, project_id: str, choice: int, correct: bool) -> bool:
    """Store the answer. Returns False if this quiz was already answered."""
    conn = get_connection()
    try:
        with conn:
            conn.execute(
                "INSERT INTO quiz_answers (quiz_id, project_id, choice, correct) VALUES (?, ?, ?, ?)",
                (quiz_id, project_id, choice, int(correct)),
            )
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def answers_for(quiz_ids: list[str]) -> dict[str, dict]:
    if not quiz_ids:
        return {}
    conn = get_connection()
    placeholders = ",".join("?" for _ in quiz_ids)
    rows = conn.execute(
        f"SELECT quiz_id, choice, correct FROM quiz_answers WHERE quiz_id IN ({placeholders})",
        quiz_ids,
    ).fetchall()
    conn.close()
    return {r[0]: {"choice": r[1], "correct": bool(r[2])} for r in rows}
