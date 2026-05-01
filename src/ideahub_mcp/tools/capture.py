from __future__ import annotations

import json
import sqlite3

from pydantic import BaseModel, Field, field_validator

from ideahub_mcp.tools.candidates import CandidateItem, candidates_or_empty
from ideahub_mcp.util.clock import utcnow_iso
from ideahub_mcp.util.coerce import normalize_task_ref
from ideahub_mcp.util.hashing import compute_content_hash
from ideahub_mcp.util.ids import new_ulid
from ideahub_mcp.util.types import StrList


class CaptureInput(BaseModel):
    content: str = Field(..., min_length=1)
    scope: str
    actor: str
    originator: str | None = None
    tags: StrList = Field(default_factory=list)
    actor_created: bool = False
    task_ref: str | None = None
    candidates: int = Field(default=5, ge=0, le=10)

    @field_validator("task_ref", mode="before")
    @classmethod
    def _normalize_task_ref(cls, v: object) -> object:
        return normalize_task_ref(v)


class TaskContext(BaseModel):
    task_ref: str | None
    recent_ids: list[str]


class CaptureOutput(BaseModel):
    id: str
    scope: str
    actor: str
    originator: str | None
    created_at: str
    suggested_tags: list[str]
    actor_created: bool = False
    task_ref: str | None = None
    annotate_candidates: list[CandidateItem] = Field(default_factory=list)
    related_candidates: list[CandidateItem] = Field(default_factory=list)
    task_context: TaskContext = Field(
        default_factory=lambda: TaskContext(task_ref=None, recent_ids=[])
    )


IDEMPOTENCY_SECONDS = 5


def _suggest_tags(conn: sqlite3.Connection, content: str, limit: int = 5) -> list[str]:
    rows = conn.execute("SELECT tags FROM idea WHERE tags != '[]'").fetchall()
    known: set[str] = set()
    for (tags_json,) in rows:
        try:
            known.update(json.loads(tags_json))
        except json.JSONDecodeError:
            continue
    lowered = content.lower()
    return sorted([t for t in known if t.lower() in lowered])[:limit]


# Intentionally duplicated in checkpoint.py — keep in sync.
def _task_context(
    conn: sqlite3.Connection, task_ref: str | None, current_id: str
) -> TaskContext:
    if not task_ref:
        return TaskContext(task_ref=None, recent_ids=[])
    rows = conn.execute(
        "SELECT id FROM idea WHERE task_ref = ? AND id != ? "
        "ORDER BY created_at DESC LIMIT 10",
        (task_ref, current_id),
    ).fetchall()
    return TaskContext(task_ref=task_ref, recent_ids=[r[0] for r in rows])


def _dedup_response(
    conn: sqlite3.Connection,
    input_: CaptureInput,
    existing_id: str,
    existing_created_at: str,
) -> CaptureOutput:
    stored_task_ref = conn.execute(
        "SELECT task_ref FROM idea WHERE id = ?", (existing_id,)
    ).fetchone()[0]
    cands = candidates_or_empty(
        conn,
        candidates=input_.candidates,
        content=input_.content,
        scope=input_.scope,
        originator=input_.originator,
        task_ref=stored_task_ref,
        exclude_id=existing_id,
    )
    return CaptureOutput(
        id=existing_id,
        scope=input_.scope,
        actor=input_.actor,
        originator=input_.originator,
        created_at=existing_created_at,
        suggested_tags=_suggest_tags(conn, input_.content),
        actor_created=input_.actor_created,
        task_ref=stored_task_ref,
        annotate_candidates=cands.annotate_candidates,
        related_candidates=cands.related_candidates,
        task_context=_task_context(conn, stored_task_ref, existing_id),
    )


def _merge_tags_into(
    conn: sqlite3.Connection, idea_id: str, incoming: list[str]
) -> list[str]:
    """Union ``incoming`` into the row's stored tags. Returns the added tags.

    The added-tags list is what the dup_attempt note records as the
    delta — if the duplicate brought no new tags, the list is empty and
    the note still records the attempt itself.
    """
    row = conn.execute("SELECT tags FROM idea WHERE id = ?", (idea_id,)).fetchone()
    try:
        existing = list(json.loads(row[0])) if row else []
    except json.JSONDecodeError:
        existing = []
    existing_set = set(existing)
    added = [t for t in incoming if t not in existing_set]
    if added:
        merged = existing + added
        conn.execute(
            "UPDATE idea SET tags = ? WHERE id = ?", (json.dumps(merged), idea_id)
        )
    return added


def capture_idea(conn: sqlite3.Connection, input_: CaptureInput) -> CaptureOutput:
    # Fast path: accidental double-fire from the same actor within 5s.
    # Cheaper than the hash lookup and intentionally silent — no dup_attempt
    # note for what is almost certainly a button-mash.
    dup = conn.execute(
        "SELECT id, created_at FROM idea "
        "WHERE actor_id = ? AND scope = ? "
        "  AND content = ? AND archived_at IS NULL "
        "  AND (julianday('now') - julianday(created_at)) * 86400 < ?",
        (input_.actor, input_.scope, input_.content, IDEMPOTENCY_SECONDS),
    ).fetchone()
    if dup:
        return _dedup_response(conn, input_, dup[0], dup[1])

    # Content-hash path: catches identical content from a different actor
    # or after the 5s window. Records a dup_attempt note so re-derivation
    # of the same idea is observable in the row's note stream.
    content_hash = compute_content_hash(input_.content)
    hash_hit = conn.execute(
        "SELECT id, created_at FROM idea "
        "WHERE scope = ? AND content_hash = ? AND archived_at IS NULL "
        "  AND kind = 'idea' "
        "ORDER BY created_at ASC LIMIT 1",
        (input_.scope, content_hash),
    ).fetchone()
    if hash_hit:
        added_tags = _merge_tags_into(conn, hash_hit[0], list(input_.tags))
        note_id = new_ulid()
        attempt_note = (
            f"actor={input_.actor}; "
            f"task_ref={input_.task_ref}; "
            f"added_tags={added_tags}"
        )
        conn.execute(
            "INSERT INTO idea_note "
            "(id, idea_id, kind, content, actor_id, originator_id, "
            " created_at, task_ref) "
            "VALUES (?, ?, 'dup_attempt', ?, ?, ?, ?, ?)",
            (
                note_id,
                hash_hit[0],
                attempt_note,
                input_.actor,
                input_.originator,
                utcnow_iso(),
                input_.task_ref,
            ),
        )
        return _dedup_response(conn, input_, hash_hit[0], hash_hit[1])

    new_id = new_ulid()
    now = utcnow_iso()
    conn.execute(
        "INSERT INTO idea "
        "(id, content, scope, actor_id, originator_id, tags, created_at, "
        " task_ref, content_hash) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            new_id,
            input_.content,
            input_.scope,
            input_.actor,
            input_.originator,
            json.dumps(input_.tags),
            now,
            input_.task_ref,
            content_hash,
        ),
    )
    cands = candidates_or_empty(
        conn,
        candidates=input_.candidates,
        content=input_.content,
        scope=input_.scope,
        originator=input_.originator,
        task_ref=input_.task_ref,
        exclude_id=new_id,
    )
    return CaptureOutput(
        id=new_id,
        scope=input_.scope,
        actor=input_.actor,
        originator=input_.originator,
        created_at=now,
        suggested_tags=_suggest_tags(conn, input_.content),
        actor_created=input_.actor_created,
        task_ref=input_.task_ref,
        annotate_candidates=cands.annotate_candidates,
        related_candidates=cands.related_candidates,
        task_context=_task_context(conn, input_.task_ref, new_id),
    )
