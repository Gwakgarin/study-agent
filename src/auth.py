"""User accounts and login sessions, stored next to the rest of the app data in SQLite.

Passwords are hashed with scrypt (stdlib, salted per user). Login tokens live only in the
browser cookie; the database keeps their SHA-256 so a leaked DB file can't be replayed.
"""

import hashlib
import hmac
import re
import secrets
import sqlite3
import uuid

from src.config import settings

DB_PATH = settings.db_path

USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{3,20}$")
MIN_PASSWORD_LENGTH = 8
SESSION_DAYS = 30

_SCRYPT_N, _SCRYPT_R, _SCRYPT_P = 2**14, 8, 1


class SignupError(ValueError):
    """Signup input was rejected; the message is safe to show to the user."""


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS logins (
            token_hash TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            expires_at TEXT NOT NULL
        )
        """
    )
    return conn


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P)
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, n, r, p, salt_hex, digest_hex = stored.split("$")
        digest = hashlib.scrypt(
            password.encode(), salt=bytes.fromhex(salt_hex), n=int(n), r=int(r), p=int(p)
        )
    except ValueError:
        return False
    return hmac.compare_digest(digest.hex(), digest_hex)


def create_user(username: str, password: str) -> dict:
    if not USERNAME_PATTERN.match(username):
        raise SignupError("아이디는 영문, 숫자, 밑줄(_)로 3~20자여야 해요.")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise SignupError(f"비밀번호는 {MIN_PASSWORD_LENGTH}자 이상이어야 해요.")

    user_id = str(uuid.uuid4())
    conn = get_connection()
    try:
        with conn:
            conn.execute(
                "INSERT INTO users (id, username, password_hash) VALUES (?, ?, ?)",
                (user_id, username, hash_password(password)),
            )
    except sqlite3.IntegrityError as exc:
        raise SignupError("이미 사용 중인 아이디예요.") from exc
    finally:
        conn.close()
    return {"id": user_id, "username": username}


def authenticate(username: str, password: str) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT id, username, password_hash FROM users WHERE username = ?", (username,)
    ).fetchone()
    conn.close()
    if row is None:
        # Hash anyway so an unknown username takes as long as a wrong password.
        hash_password(password)
        return None
    if not verify_password(password, row[2]):
        return None
    return {"id": row[0], "username": row[1]}


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_login(user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    conn = get_connection()
    with conn:
        conn.execute(
            "INSERT INTO logins (token_hash, user_id, expires_at) VALUES (?, ?, datetime('now', ?))",
            (_token_hash(token), user_id, f"+{SESSION_DAYS} days"),
        )
    conn.close()
    return token


def user_for_token(token: str | None) -> dict | None:
    if not token:
        return None
    conn = get_connection()
    row = conn.execute(
        """
        SELECT users.id, users.username
        FROM logins JOIN users ON users.id = logins.user_id
        WHERE logins.token_hash = ? AND logins.expires_at > datetime('now')
        """,
        (_token_hash(token),),
    ).fetchone()
    conn.close()
    return {"id": row[0], "username": row[1]} if row else None


def delete_login(token: str | None) -> None:
    if not token:
        return
    conn = get_connection()
    with conn:
        conn.execute("DELETE FROM logins WHERE token_hash = ?", (_token_hash(token),))
    conn.close()


if __name__ == "__main__":
    import sys

    from src.projects import claim_unowned_projects

    if len(sys.argv) != 3 or sys.argv[1] != "claim":
        raise SystemExit("Usage: python -m src.auth claim <username>")
    conn = get_connection()
    row = conn.execute("SELECT id FROM users WHERE username = ?", (sys.argv[2],)).fetchone()
    conn.close()
    if row is None:
        raise SystemExit(f"No user named {sys.argv[2]}")
    print(f"Moved {claim_unowned_projects(row[0])} project(s) to {sys.argv[2]}.")
