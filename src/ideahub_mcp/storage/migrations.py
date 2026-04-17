from __future__ import annotations

import sqlite3
from pathlib import Path


def apply_pending_migrations(conn: sqlite3.Connection, migrations_dir: Path) -> list[str]:
    """Apply every migration in migrations_dir not yet in schema_version, in lexical order.

    Returns the list of applied migration names.
    """
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_version ("
        "  name TEXT PRIMARY KEY,"
        "  applied_at TEXT NOT NULL"
        ")"
    )
    applied = {
        row[0] for row in conn.execute("SELECT name FROM schema_version").fetchall()
    }

    if not migrations_dir.exists():
        return []

    pending = sorted(p for p in migrations_dir.glob("*.sql") if p.name not in applied)
    names_applied: list[str] = []
    for path in pending:
        sql = path.read_text()
        conn.executescript(sql)
        conn.execute(
            "INSERT INTO schema_version (name, applied_at) VALUES (?, datetime('now'))",
            (path.name,),
        )
        names_applied.append(path.name)
    return names_applied
