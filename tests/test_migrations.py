from __future__ import annotations

from pathlib import Path

from ideahub_mcp.storage.connection import open_connection
from ideahub_mcp.storage.migrations import apply_pending_migrations

MIGRATIONS_DIR = (
    Path(__file__).resolve().parents[1] / "src" / "ideahub_mcp" / "storage" / "migrations"
)


def test_apply_pending_migrations_creates_schema_version_table(tmp_path: Path) -> None:
    db = tmp_path / "t.db"
    with open_connection(db) as conn:
        apply_pending_migrations(conn, tmp_path / "no_migrations")
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
        ).fetchall()
    assert rows == [("schema_version",)]


def test_apply_pending_migrations_is_idempotent(tmp_path: Path) -> None:
    db = tmp_path / "t.db"
    with open_connection(db) as conn:
        apply_pending_migrations(conn, tmp_path / "no_migrations")
        apply_pending_migrations(conn, tmp_path / "no_migrations")


def test_001_init_creates_all_tables(tmp_path: Path) -> None:
    db = tmp_path / "t.db"
    with open_connection(db) as conn:
        apply_pending_migrations(conn, MIGRATIONS_DIR)
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    assert {"actor", "idea", "idea_note", "idea_link", "idea_fts", "schema_version"} <= tables


def test_001_init_fts_insert_roundtrip(tmp_path: Path) -> None:
    db = tmp_path / "t.db"
    with open_connection(db) as conn:
        apply_pending_migrations(conn, MIGRATIONS_DIR)
        conn.execute(
            "INSERT INTO actor (id, kind, display_name, first_seen_at) "
            "VALUES ('human:m', 'human', 'M', datetime('now'))"
        )
        conn.execute(
            "INSERT INTO idea (id, content, scope, actor_id, created_at) "
            "VALUES ('01H', 'model-facing interface', 'global', 'human:m', datetime('now'))"
        )
        hits = conn.execute(
            "SELECT rowid FROM idea_fts WHERE idea_fts MATCH 'model'"
        ).fetchall()
    assert len(hits) == 1
