"""SQLite-backed tracking of quiz answers and a spaced-repetition review schedule."""

import sqlite3

from src.config import settings

DB_PATH = settings.db_path

# Simplified SM-2: no manual quality rating, just correct/incorrect.
MIN_EASE_FACTOR = 1.3
DEFAULT_EASE_FACTOR = 2.5


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT NOT NULL,
            topic TEXT NOT NULL,
            correct INTEGER NOT NULL,
            answered_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schedule (
            project_id TEXT NOT NULL,
            topic TEXT NOT NULL,
            repetitions INTEGER NOT NULL DEFAULT 0,
            interval_days REAL NOT NULL DEFAULT 0,
            ease_factor REAL NOT NULL DEFAULT 2.5,
            next_review_at TEXT NOT NULL DEFAULT (datetime('now')),
            PRIMARY KEY (project_id, topic)
        )
        """
    )
    return conn


def _next_schedule(repetitions: int, interval_days: float, ease_factor: float, correct: bool):
    if correct:
        repetitions += 1
        if repetitions == 1:
            interval_days = 1
        elif repetitions == 2:
            interval_days = 6
        else:
            interval_days = round(interval_days * ease_factor)
        ease_factor = min(3.0, ease_factor + 0.1)
    else:
        repetitions = 0
        interval_days = 1
        ease_factor = max(MIN_EASE_FACTOR, ease_factor - 0.2)
    return repetitions, interval_days, ease_factor


def record_answer(project_id: str, topic: str, correct: bool) -> None:
    conn = get_connection()
    with conn:
        conn.execute(
            "INSERT INTO answers (project_id, topic, correct) VALUES (?, ?, ?)",
            (project_id, topic, int(correct)),
        )

        row = conn.execute(
            "SELECT repetitions, interval_days, ease_factor FROM schedule WHERE project_id = ? AND topic = ?",
            (project_id, topic),
        ).fetchone()
        repetitions, interval_days, ease_factor = row or (0, 0, DEFAULT_EASE_FACTOR)

        repetitions, interval_days, ease_factor = _next_schedule(
            repetitions, interval_days, ease_factor, correct
        )

        conn.execute(
            """
            INSERT INTO schedule (project_id, topic, repetitions, interval_days, ease_factor, next_review_at)
            VALUES (?, ?, ?, ?, ?, datetime('now', ? || ' days'))
            ON CONFLICT(project_id, topic) DO UPDATE SET
                repetitions = excluded.repetitions,
                interval_days = excluded.interval_days,
                ease_factor = excluded.ease_factor,
                next_review_at = excluded.next_review_at
            """,
            (project_id, topic, repetitions, interval_days, ease_factor, str(interval_days)),
        )
    conn.close()


def _adjusted_wrong_rate(wrong: int, attempts: int) -> float:
    """Laplace (add-one) smoothed wrong rate.

    Raw wrong_rate treats a single miss (1/1 = 100%) as a stronger signal
    than 9 misses out of 10 (90%), even though the second has far more
    evidence behind it. Adding one hypothetical right and one hypothetical
    wrong answer before any real data pulls low-attempt topics toward 50%,
    so a topic needs more attempts behind it to rank as a top weak spot.
    wrong_rate itself is left untouched for display — only ranking uses this.
    """
    return (wrong + 1) / (attempts + 2)


def get_weak_topics(project_id: str, limit: int = 5) -> list[dict]:
    """Return topics ranked by adjusted_wrong_rate, worst first.

    Topics answered only once are included so a single miss on a new
    topic still surfaces, but the ranking discounts topics with few
    attempts so they don't outrank topics with more, worse, evidence.
    See _adjusted_wrong_rate for the smoothing this relies on.
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
        WHERE project_id = ?
        GROUP BY topic
        HAVING wrong > 0
        """,
        (project_id,),
    ).fetchall()
    conn.close()

    topics = [
        {
            "topic": r[0],
            "attempts": r[1],
            "wrong": r[2],
            "wrong_rate": r[3],
            "adjusted_wrong_rate": _adjusted_wrong_rate(r[2], r[1]),
        }
        for r in rows
    ]
    topics.sort(key=lambda t: (-t["adjusted_wrong_rate"], -t["attempts"], t["topic"]))
    return topics[:limit]


def get_due_topics(project_id: str) -> list[dict]:
    """Topics whose spaced-repetition schedule says they're due for review now."""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT topic, next_review_at
        FROM schedule
        WHERE project_id = ? AND next_review_at <= datetime('now')
        ORDER BY next_review_at ASC
        """,
        (project_id,),
    ).fetchall()
    conn.close()

    return [{"topic": r[0], "next_review_at": r[1]} for r in rows]
