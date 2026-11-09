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
GUEST_PREFIX = "guest_"

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
    columns = {row[1] for row in conn.execute("PRAGMA table_info(users)")}
    if "is_guest" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN is_guest INTEGER NOT NULL DEFAULT 0")
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


def _check_signup(username: str, password: str) -> None:
    if not USERNAME_PATTERN.match(username):
        raise SignupError("아이디는 영문, 숫자, 밑줄(_)로 3~20자여야 해요.")
    if username.lower().startswith(GUEST_PREFIX):
        raise SignupError(f"{GUEST_PREFIX}로 시작하는 아이디는 쓸 수 없어요.")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise SignupError(f"비밀번호는 {MIN_PASSWORD_LENGTH}자 이상이어야 해요.")


def create_user(username: str, password: str) -> dict:
    _check_signup(username, password)

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
    return {"id": user_id, "username": username, "is_guest": False}


def create_guest() -> dict:
    """An account with no password, so someone can try the app before signing up."""
    user_id = str(uuid.uuid4())
    username = GUEST_PREFIX + secrets.token_hex(4)
    conn = get_connection()
    with conn:
        # "!" never matches a scrypt hash, so nobody can log in to a guest with a password.
        conn.execute(
            "INSERT INTO users (id, username, password_hash, is_guest) VALUES (?, ?, '!', 1)",
            (user_id, username),
        )
    conn.close()
    return {"id": user_id, "username": username, "is_guest": True}


def upgrade_guest(user_id: str, username: str, password: str) -> dict:
    """Give a guest a username and password; their subjects and review history stay as they are."""
    _check_signup(username, password)
    conn = get_connection()
    try:
        with conn:
            cur = conn.execute(
                "UPDATE users SET username = ?, password_hash = ?, is_guest = 0 WHERE id = ? AND is_guest = 1",
                (username, hash_password(password), user_id),
            )
    except sqlite3.IntegrityError as exc:
        raise SignupError("이미 사용 중인 아이디예요.") from exc
    finally:
        conn.close()
    if cur.rowcount == 0:
        raise SignupError("이미 저장된 계정이에요.")
    return {"id": user_id, "username": username, "is_guest": False}


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
    return {"id": row[0], "username": row[1], "is_guest": False}


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
        SELECT users.id, users.username, users.is_guest
        FROM logins JOIN users ON users.id = logins.user_id
        WHERE logins.token_hash = ? AND logins.expires_at > datetime('now')
        """,
        (_token_hash(token),),
    ).fetchone()
    conn.close()
    return {"id": row[0], "username": row[1], "is_guest": bool(row[2])} if row else None


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
