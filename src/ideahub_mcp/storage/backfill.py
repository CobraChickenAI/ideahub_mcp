"""Python migration steps that need to run computed values, not just DDL."""

from __future__ import annotations

import sqlite3

from ideahub_mcp.util.hashing import compute_content_hash


def backfill_content_hashes(conn: sqlite3.Connection) -> int:
    """Populate ``idea.content_hash`` for any rows where it is NULL.

    Idempotent: only updates rows whose hash has not yet been computed, so
    repeat invocations are no-ops. The hash function is the runtime
    canonical one — keep this as the single source of truth so future
    captures and the backfill stay byte-identical.

    Returns the number of rows updated.
    """
    rows = conn.execute(
        "SELECT id, content FROM idea WHERE content_hash IS NULL"
    ).fetchall()
    updated = 0
    for idea_id, content in rows:
        conn.execute(
            "UPDATE idea SET content_hash = ? WHERE id = ?",
            (compute_content_hash(content), idea_id),
        )
        updated += 1
    return updated
