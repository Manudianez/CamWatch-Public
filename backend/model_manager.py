from .database import connect


def add_model(username, platform="Stripchat"):
    """Registra un modelo. Devuelve False si ya estaba registrado."""
    with connect() as connection:
        cursor = connection.execute(
            """
            INSERT OR IGNORE INTO models
            (username, platform, status, last_seen)
            VALUES (?, ?, ?, ?)
            """,
            (username, platform, "UNKNOWN", None),
        )
        return cursor.rowcount > 0


def remove_model(username):
    with connect() as connection:
        connection.execute("DELETE FROM models WHERE username = ?", (username,))


def list_models():
    with connect() as connection:
        return connection.execute("""
            SELECT id, username, platform, status, last_seen
            FROM models
            ORDER BY username
        """).fetchall()


def update_status(username, status, last_seen=None):
    with connect() as connection:
        connection.execute(
            """
            UPDATE models
            SET status = ?, last_seen = COALESCE(?, last_seen)
            WHERE username = ?
            """,
            (status, last_seen, username),
        )


def add_tip(model, message_id, username, amount, body, created_at):
    """Guarda una propina. Devuelve False si ya estaba guardada."""
    with connect() as connection:
        cursor = connection.execute(
            """
            INSERT OR IGNORE INTO tips
            (message_id, model, username, amount, body, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (f"{model}:{message_id}", model, username, amount, body, created_at),
        )
        return cursor.rowcount > 0


def tip_summary(model, today_start, limit=30):
    """Totales de tokens y últimas propinas de un modelo."""
    with connect() as connection:
        total = connection.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM tips WHERE model = ?", (model,)
        ).fetchone()[0]
        today = connection.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM tips WHERE model = ? AND created_at >= ?",
            (model, today_start),
        ).fetchone()[0]
        recent = connection.execute(
            """
            SELECT username, amount, body, created_at FROM tips
            WHERE model = ? ORDER BY created_at DESC LIMIT ?
            """,
            (model, limit),
        ).fetchall()
    return {
        "total": total,
        "today": today,
        "recent": [
            {"username": r[0], "amount": r[1], "body": r[2], "created_at": r[3]}
            for r in recent
        ],
    }
