"""Link kinds part_of and answers, and migration 005 that allows them in the database."""

from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

import pytest

from ideahub_mcp.domain.actors import resolve_actor
from ideahub_mcp.errors import IdeaHubError
from ideahub_mcp.storage.connection import open_connection
from ideahub_mcp.storage.migrations import apply_pending_migrations
from ideahub_mcp.tools.capture import CaptureInput, capture_idea
from ideahub_mcp.tools.get import GetInput, get_idea
from ideahub_mcp.tools.link import LINK_KINDS, LinkInput, link_ideas

MIGRATIONS_DIR = (
    Path(__file__).resolve().parents[1] / "src" / "ideahub_mcp" / "storage" / "migrations"
)
M005 = "005_link_kinds_part_of_answers.sql"
LINK_DUMP = (
    "SELECT rowid, source_idea_id, target_idea_id, kind, created_at, task_ref "
    "FROM idea_link ORDER BY rowid"
)


def _two(conn: sqlite3.Connection) -> tuple[str, str]:
    resolve_actor(conn, explicit="human:m", client_info_name=None)
    a = capture_idea(conn, CaptureInput(content="part", actor="human:m", scope="global"))
    b = capture_idea(conn, CaptureInput(content="whole", actor="human:m", scope="global"))
    return a.id, b.id


# --- tool -------------------------------------------------------------------


def test_link_kinds_set() -> None:
    expected = {"related", "supersedes", "evolved_from", "duplicate", "part_of", "answers"}
    assert expected == LINK_KINDS


@pytest.mark.parametrize("kind", ["part_of", "answers"])
def test_new_kinds_accepted_and_keep_direction(conn: sqlite3.Connection, kind: str) -> None:
    a, b = _two(conn)
    # Use the larger id as source so any canonical reordering would show.
    src, tgt = max(a, b), min(a, b)
    out = link_ideas(conn, LinkInput(source_id=src, target_id=tgt, kind=kind))
    assert out.created is True
    assert (out.source_id, out.target_id, out.kind) == (src, tgt, kind)
    stored = conn.execute(
        "SELECT source_idea_id, target_idea_id FROM idea_link WHERE kind = ?", (kind,)
    ).fetchall()
    assert stored == [(src, tgt)]
    got = get_idea(conn, GetInput(id=src))
    assert [(link.target_idea_id, link.kind) for link in got.links] == [(tgt, kind)]
    again = link_ideas(conn, LinkInput(source_id=src, target_id=tgt, kind=kind))
    assert again.created is False


def test_unknown_kind_still_rejected_by_tool(conn: sqlite3.Connection) -> None:
    a, b = _two(conn)
    with pytest.raises(IdeaHubError) as exc:
        link_ideas(conn, LinkInput(source_id=a, target_id=b, kind="blocks"))
    assert exc.value.code == "invalid_link"


@pytest.mark.parametrize("kind", ["part_of", "answers"])
def test_self_link_rejected_for_new_kinds(conn: sqlite3.Connection, kind: str) -> None:
    a, _ = _two(conn)
    with pytest.raises(IdeaHubError) as exc:
        link_ideas(conn, LinkInput(source_id=a, target_id=a, kind=kind))
    assert exc.value.code == "invalid_link"


# --- database rule ------------------------------------------------------------


def _raw_insert(conn: sqlite3.Connection, src: str, tgt: str, kind: str) -> None:
    conn.execute(
        "INSERT INTO idea_link (source_idea_id, target_idea_id, kind, created_at) "
        "VALUES (?, ?, ?, '2026-10-25T00:00:00Z')",
        (src, tgt, kind),
    )


@pytest.mark.parametrize("kind", ["part_of", "answers"])
def test_db_accepts_new_kinds(conn: sqlite3.Connection, kind: str) -> None:
    a, b = _two(conn)
    _raw_insert(conn, a, b, kind)


def test_db_rejects_unknown_kind(conn: sqlite3.Connection) -> None:
    a, b = _two(conn)
    with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
        _raw_insert(conn, a, b, "blocks")


# --- migration 005 --------------------------------------------------------------


def _store_at_004(tmp_path: Path) -> Path:
    """A store migrated through 004 only, holding links of all four old kinds."""
    old_dir = tmp_path / "migrations_004"
    old_dir.mkdir()
    for p in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if p.name < "005":
            shutil.copy(p, old_dir / p.name)
    db = tmp_path / "store.db"
    with open_connection(db) as c:
        assert M005 not in apply_pending_migrations(c, old_dir)
        c.execute(
            "INSERT INTO actor (id, kind, display_name, first_seen_at) "
            "VALUES ('human:m', 'human', 'M', '2026-10-01T00:00:00Z')"
        )
        for i in range(1, 7):
            c.execute(
                "INSERT INTO idea (id, content, scope, actor_id, created_at) "
                "VALUES (?, ?, 'global', 'human:m', ?)",
                (f"I{i}", f"idea number {i}", f"2026-10-0{i}T00:00:00Z"),
            )
        c.execute(
            "INSERT INTO idea_note (id, idea_id, content, actor_id, created_at) "
            "VALUES ('N1', 'I1', 'a note', 'human:m', '2026-10-02T00:00:00Z')"
        )
        rows = [
            ("I1", "I2", "related", "2026-10-03T01:02:03Z", None),
            ("I3", "I2", "supersedes", "2026-10-03T01:02:04Z", "task-a"),
            ("I4", "I1", "evolved_from", "2026-10-03T01:02:05Z", None),
            ("I5", "I6", "duplicate", "2026-10-03T01:02:06Z", "task-b"),
            ("I1", "I2", "supersedes", "2026-10-03T01:02:07Z", None),
            ("I2", "I6", "related", "2026-10-03T01:02:08Z", "task-a"),
        ]
        c.executemany(
            "INSERT INTO idea_link (source_idea_id, target_idea_id, kind, created_at, task_ref) "
            "VALUES (?, ?, ?, ?, ?)",
            rows,
        )
        # Leave a gap in rowids so the test proves rowids survive the copy.
        c.execute("DELETE FROM idea_link WHERE kind = 'evolved_from'")
        c.execute(
            "INSERT INTO idea_link (source_idea_id, target_idea_id, kind, created_at) "
            "VALUES ('I4', 'I1', 'evolved_from', '2026-10-03T01:02:09Z')"
        )
    return db


def _snapshot(c: sqlite3.Connection) -> dict[str, object]:
    return {
        "links": c.execute(LINK_DUMP).fetchall(),
        "ideas": c.execute("SELECT * FROM idea ORDER BY id").fetchall(),
        "notes": c.execute("SELECT * FROM idea_note ORDER BY id").fetchall(),
        "actors": c.execute("SELECT * FROM actor ORDER BY id").fetchall(),
    }


def _versions(c: sqlite3.Connection) -> set[str]:
    return {r[0] for r in c.execute("SELECT name FROM schema_version")}


def test_005_preserves_every_row_and_schema(tmp_path: Path) -> None:
    db = _store_at_004(tmp_path)
    with open_connection(db) as c:
        before = _snapshot(c)
        cols_before = c.execute("PRAGMA table_info(idea_link)").fetchall()
        assert M005 not in _versions(c)
        with pytest.raises(sqlite3.IntegrityError):
            _raw_insert(c, "I1", "I3", "part_of")

        assert apply_pending_migrations(c, MIGRATIONS_DIR) == [M005]

        assert _snapshot(c) == before  # kind, created_at, task_ref, rowid: all identical
        assert len(before["links"]) == 6  # type: ignore[arg-type]
        assert M005 in _versions(c)
        assert c.execute("PRAGMA table_info(idea_link)").fetchall() == cols_before
        pk = [r[1] for r in sorted(cols_before, key=lambda r: r[5]) if r[5]]
        assert pk == ["source_idea_id", "target_idea_id", "kind"]
        fks = c.execute("PRAGMA foreign_key_list(idea_link)").fetchall()
        assert sorted((r[3], r[2], r[4], r[6]) for r in fks) == [
            ("source_idea_id", "idea", "id", "CASCADE"),
            ("target_idea_id", "idea", "id", "CASCADE"),
        ]
        assert c.execute("PRAGMA foreign_key_check").fetchall() == []
        assert c.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert c.execute("PRAGMA foreign_keys").fetchone() == (1,)
        assert not c.execute(
            "SELECT 1 FROM sqlite_master WHERE name = 'idea_link_new'"
        ).fetchone()

        # New kinds now pass the database rule; unknown still fails.
        _raw_insert(c, "I1", "I3", "part_of")
        _raw_insert(c, "I3", "I4", "answers")
        with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
            _raw_insert(c, "I1", "I4", "blocks")

        # Composite PK still enforced.
        with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"):
            _raw_insert(c, "I1", "I3", "part_of")

        # ON DELETE CASCADE still works: deleting I2 removes exactly its links.
        c.execute("DELETE FROM idea WHERE id = 'I2'")
        left = {(r[1], r[2], r[3]) for r in c.execute(LINK_DUMP)}
        assert all("I2" not in (s, t) for s, t, _ in left)
        assert ("I5", "I6", "duplicate") in left
        assert ("I1", "I3", "part_of") in left


def test_005_rebuild_deletes_nothing_with_foreign_keys_on(tmp_path: Path) -> None:
    """The runner keeps foreign_keys ON. Dropping idea_link must not cascade."""
    db = _store_at_004(tmp_path)
    with open_connection(db) as c:
        assert c.execute("PRAGMA foreign_keys").fetchone() == (1,)
        counts = [
            c.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
            for t in ("actor", "idea", "idea_note", "idea_link")
        ]
        apply_pending_migrations(c, MIGRATIONS_DIR)
        after = [
            c.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
            for t in ("actor", "idea", "idea_note", "idea_link")
        ]
        hits = c.execute("SELECT rowid FROM idea_fts WHERE idea_fts MATCH 'number'").fetchall()
    assert after == counts
    assert len(hits) == 6


def test_005_runner_is_idempotent(tmp_path: Path) -> None:
    db = _store_at_004(tmp_path)
    with open_connection(db) as c:
        apply_pending_migrations(c, MIGRATIONS_DIR)
        snap = _snapshot(c)
        assert apply_pending_migrations(c, MIGRATIONS_DIR) == []
        assert _snapshot(c) == snap
    with open_connection(db) as c:  # a fresh process start
        assert apply_pending_migrations(c, MIGRATIONS_DIR) == []
        assert _snapshot(c) == snap


def test_005_rerun_after_commit_without_version_row_is_safe(tmp_path: Path) -> None:
    """If a start stopped after 005 committed but before schema_version was written."""
    db = _store_at_004(tmp_path)
    with open_connection(db) as c:
        apply_pending_migrations(c, MIGRATIONS_DIR)
        _raw_insert(c, "I1", "I3", "part_of")
        snap = _snapshot(c)
        c.execute("DELETE FROM schema_version WHERE name = ?", (M005,))
        assert apply_pending_migrations(c, MIGRATIONS_DIR) == [M005]
        assert _snapshot(c) == snap


def test_005_failure_leaves_old_table_intact(tmp_path: Path) -> None:
    """An orphan link (possible only if written with foreign keys off) stops 005
    and the transaction rolls back: old table and rows unchanged, 005 not recorded."""
    db = _store_at_004(tmp_path)
    raw = sqlite3.connect(db, isolation_level=None)
    raw.execute("PRAGMA foreign_keys=OFF")
    raw.execute(
        "INSERT INTO idea_link (source_idea_id, target_idea_id, kind, created_at) "
        "VALUES ('I1', 'GONE', 'related', '2026-10-04T00:00:00Z')"
    )
    raw.close()
    with open_connection(db) as c:
        before = _snapshot(c)
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
            apply_pending_migrations(c, MIGRATIONS_DIR)
    with open_connection(db) as c:
        assert _snapshot(c) == before
        assert M005 not in _versions(c)
        sql = c.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'idea_link'"
        ).fetchone()[0]
        assert "part_of" not in sql
        assert not c.execute(
            "SELECT 1 FROM sqlite_master WHERE name = 'idea_link_new'"
        ).fetchone()


def test_fresh_store_gets_new_schema(tmp_path: Path) -> None:
    with open_connection(tmp_path / "fresh.db") as c:
        applied = apply_pending_migrations(c, MIGRATIONS_DIR)
        assert applied[-1] == M005
        sql = c.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'idea_link'"
        ).fetchone()[0]
        cols = [r[1] for r in c.execute("PRAGMA table_info(idea_link)")]
    assert "'part_of','answers'" in sql
    assert cols == ["source_idea_id", "target_idea_id", "kind", "created_at", "task_ref"]
