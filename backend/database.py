import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .config import Config

DB_PATH = Path(__file__).resolve().parent.parent / "database" / f"{Config.APP}.db"

SESSION_FIELDS = (
    "sid", "install_id", "state", "verifier", "account_id", "account_name",
    "access_token", "refresh_token", "expires_at",
)


@contextmanager
def connect():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def initialize_database():
    DB_PATH.parent.mkdir(exist_ok=True)

    with connect() as connection:
        # Una fila por navegador que ha iniciado (o está iniciando) sesión.
        connection.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                sid TEXT PRIMARY KEY,
                install_id TEXT NOT NULL,
                state TEXT,
                verifier TEXT,
                account_id TEXT,
                account_name TEXT,
                access_token TEXT,
                refresh_token TEXT,
                expires_at REAL
            )
        """)
        # Modelos que sigue cada cuenta de Statbate.
        connection.execute("""
            CREATE TABLE IF NOT EXISTS follows (
                account_id TEXT NOT NULL,
                username TEXT NOT NULL,
                PRIMARY KEY (account_id, username)
            )
        """)


def get_session(sid):
    if not sid:
        return None
    with connect() as connection:
        row = connection.execute("SELECT * FROM sessions WHERE sid = ?", (sid,)).fetchone()
    return dict(row) if row else None


def save_session(session):
    with connect() as connection:
        connection.execute(
            f"INSERT OR REPLACE INTO sessions ({', '.join(SESSION_FIELDS)}) "
            f"VALUES ({', '.join('?' for _ in SESSION_FIELDS)})",
            tuple(session.get(field) for field in SESSION_FIELDS),
        )


def delete_session(sid):
    """Borra la sesión y, si era la última de esa cuenta, también sus datos."""
    with connect() as connection:
        row = connection.execute(
            "SELECT account_id FROM sessions WHERE sid = ?", (sid,)
        ).fetchone()
        connection.execute("DELETE FROM sessions WHERE sid = ?", (sid,))
        if row and row["account_id"]:
            others = connection.execute(
                "SELECT 1 FROM sessions WHERE account_id = ? LIMIT 1", (row["account_id"],)
            ).fetchone()
            if not others:
                connection.execute(
                    "DELETE FROM follows WHERE account_id = ?", (row["account_id"],)
                )


def list_follows(account_id):
    with connect() as connection:
        rows = connection.execute(
            "SELECT username FROM follows WHERE account_id = ? ORDER BY username COLLATE NOCASE",
            (account_id,),
        ).fetchall()
    return [row["username"] for row in rows]


def add_follow(account_id, username):
    with connect() as connection:
        connection.execute(
            "INSERT OR IGNORE INTO follows (account_id, username) VALUES (?, ?)",
            (account_id, username),
        )


def remove_follow(account_id, username):
    with connect() as connection:
        connection.execute(
            "DELETE FROM follows WHERE account_id = ? AND username = ?",
            (account_id, username),
        )
