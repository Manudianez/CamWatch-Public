import sqlite3
from pathlib import Path

DB_PATH = Path("database/stripwatch.db")


def initialize_database():
    DB_PATH.parent.mkdir(exist_ok=True)

    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS models (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            platform TEXT,
            status TEXT,
            last_seen TEXT
        )
    """)

    connection.commit()
    connection.close()