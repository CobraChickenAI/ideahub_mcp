from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass

from ideahub_mcp.util.clock import utcnow_iso


class ActorUnresolvedError(Exception):
    code = "actor_unresolved"
    fix = "Pass `actor` or set IDEAHUB_ACTOR."


@dataclass(frozen=True)
class ResolvedActor:
    id: str
    kind: str
    display_name: str
    created: bool


def _kind_from_id(actor_id: str) -> str:
    if actor_id.startswith("agent:"):
        return "agent"
    if actor_id.startswith("human:"):
        return "human"
    raise ValueError(
        f"Actor id must be prefixed with 'agent:' or 'human:': {actor_id!r}"
    )


def resolve_actor(
    conn: sqlite3.Connection,
    explicit: str | None,
    client_info_name: str | None,
) -> ResolvedActor:
    actor_id: str
    if explicit:
        actor_id = explicit
    elif client_info_name:
        actor_id = f"agent:{client_info_name}"
    elif env := os.getenv("IDEAHUB_ACTOR"):
        actor_id = env
    else:
        raise ActorUnresolvedError(
            "Cannot determine actor; pass `actor` or set IDEAHUB_ACTOR."
        )

    kind = _kind_from_id(actor_id)
    row = conn.execute(
        "SELECT kind, display_name FROM actor WHERE id = ?", (actor_id,)
    ).fetchone()
    if row is not None:
        return ResolvedActor(
            id=actor_id, kind=row[0], display_name=row[1], created=False
        )

    display = actor_id.split(":", 1)[1]
    conn.execute(
        "INSERT INTO actor (id, kind, display_name, first_seen_at) VALUES (?, ?, ?, ?)",
        (actor_id, kind, display, utcnow_iso()),
    )
    return ResolvedActor(id=actor_id, kind=kind, display_name=display, created=True)
