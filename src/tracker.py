"""SQLite-backed tracking of quiz answers, used to find weak topics to prioritize."""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "tracker.db"


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT NOT NULL,
            correct INTEGER NOT NULL,
            answered_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    return conn


def record_answer(topic: str, correct: bool) -> None:
    conn = get_connection()
    with conn:
        conn.execute(
            "INSERT INTO answers (topic, correct) VALUES (?, ?)",
            (topic, int(correct)),
        )
    conn.close()


def get_weak_topics(limit: int = 5) -> list[dict]:
    """Return topics ordered by wrong-answer rate, worst first.

    Topics answered only once are included so a single miss on a new
    topic still surfaces, but topics with more attempts are considered
    more reliable signals than one-off answers.
    """
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT
            topic,
            COUNT(*) AS attempts,
            SUM(1 - correct) AS wrong,
            CAST(SUM(1 - correct) AS FLOAT) / COUNT(*) AS wrong_rate
        FROM answers
        GROUP BY topic
        HAVING wrong > 0
        ORDER BY wrong_rate DESC, attempts DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()

    return [
        {"topic": r[0], "attempts": r[1], "wrong": r[2], "wrong_rate": r[3]}
        for r in rows
    ]
