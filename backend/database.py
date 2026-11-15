import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "database" / "stripwatch.db"


@contextmanager
def connect():
    connection = sqlite3.connect(DB_PATH)
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def initialize_database():
    DB_PATH.parent.mkdir(exist_ok=True)

    with connect() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS models (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                platform TEXT,
                status TEXT,
                last_seen TEXT
            )
        """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS tips (
                message_id TEXT PRIMARY KEY,
                model TEXT NOT NULL,
                username TEXT,
                amount INTEGER NOT NULL,
                body TEXT,
                created_at TEXT NOT NULL
            )
        """)
        connection.execute(
            "CREATE INDEX IF NOT EXISTS tips_model ON tips (model, created_at)"
        )
