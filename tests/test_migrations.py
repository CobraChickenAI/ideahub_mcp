from __future__ import annotations

import sqlite3
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


def test_migration_002_adds_kind_and_task_ref(conn: sqlite3.Connection) -> None:
    idea_cols = {r[1] for r in conn.execute("PRAGMA table_info(idea)").fetchall()}
    assert "kind" in idea_cols
    assert "task_ref" in idea_cols

    note_cols = {r[1] for r in conn.execute("PRAGMA table_info(idea_note)").fetchall()}
    assert "task_ref" in note_cols

    link_cols = {r[1] for r in conn.execute("PRAGMA table_info(idea_link)").fetchall()}
    assert "task_ref" in link_cols

    # Default for idea.kind is 'idea'
    conn.execute(
        "INSERT INTO actor (id, kind, display_name, first_seen_at) "
        "VALUES ('a1','agent','a1',datetime('now'))"
    )
    conn.execute(
        "INSERT INTO idea (id, content, scope, actor_id, tags, created_at) "
        "VALUES ('i1','x','s','a1','[]',datetime('now'))"
    )
    row = conn.execute("SELECT kind, task_ref FROM idea WHERE id='i1'").fetchone()
    assert row[0] == "idea"
    assert row[1] is None

    # Index present
    idxs = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index'"
    ).fetchall()}
    assert "idea_kind_idx" in idxs
    assert "idea_task_ref_idx" in idxs


def test_migration_004_adds_content_hash_column_and_index(
    conn: sqlite3.Connection,
) -> None:
    cols = {r[1] for r in conn.execute("PRAGMA table_info(idea)").fetchall()}
    assert "content_hash" in cols
    idxs = {
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        ).fetchall()
    }
    assert "idea_scope_hash_idx" in idxs


def test_migration_004_backfills_content_hash(tmp_path: Path) -> None:
    """Pre-existing rows without content_hash get backfilled to the canonical
    hash on migration 004 — the same value the runtime computes."""
    from ideahub_mcp.util.hashing import compute_content_hash

    db = tmp_path / "t.db"
    with open_connection(db) as c:
        # Apply only 001-003 by hand to simulate a pre-004 store.
        partial_dir = tmp_path / "migrations_partial"
        partial_dir.mkdir()
        for name in (
            "001_init.sql",
            "002_kind_and_task_ref.sql",
            "003_checkpoint_kind_label.sql",
        ):
            (partial_dir / name).write_text((MIGRATIONS_DIR / name).read_text())
        apply_pending_migrations(c, partial_dir)

        c.execute(
            "INSERT INTO actor (id, kind, display_name, first_seen_at) "
            "VALUES ('a','agent','a',datetime('now'))"
        )
        c.execute(
            "INSERT INTO idea (id, content, scope, actor_id, tags, created_at) "
            "VALUES ('i1','  Hashable Content  ','s','a','[]',datetime('now'))"
        )

        # Now apply the full migrations directory — migration 004 should run
        # and backfill content_hash for the row inserted above.
        apply_pending_migrations(c, MIGRATIONS_DIR)

        row = c.execute(
            "SELECT content_hash FROM idea WHERE id = 'i1'"
        ).fetchone()
        assert row[0] == compute_content_hash("  Hashable Content  ")
