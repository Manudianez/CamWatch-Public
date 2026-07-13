import sqlite3
from pathlib import Path

DB_PATH = Path("database/stripwatch.db")


def add_model(username, platform="Stripchat"):
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT OR IGNORE INTO models
        (username, platform, status, last_seen)
        VALUES (?, ?, ?, ?)
        """,
        (username, platform, "UNKNOWN", None),
    )

    connection.commit()
    connection.close()


def list_models():
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id, username, platform, status
        FROM models
        ORDER BY username
    """)

    models = cursor.fetchall()

    connection.close()

    return models