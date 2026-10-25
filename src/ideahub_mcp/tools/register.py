from __future__ import annotations

import sqlite3

from pydantic import BaseModel

from ideahub_mcp.domain.actors import ensure_actor
from ideahub_mcp.errors import IdeaHubError
from ideahub_mcp.tools.recognize import ActorRecord


class RegisterInput(BaseModel):
    id: str
    display_name: str | None = None


class RegisterOutput(BaseModel):
    actor: ActorRecord
    created: bool


def register_actor(conn: sqlite3.Connection, input_: RegisterInput) -> RegisterOutput:
    try:
        resolved = ensure_actor(conn, input_.id, display_name=input_.display_name)
    except ValueError as e:
        raise IdeaHubError(
            code="invalid_actor_id",
            message=str(e),
            fix="Use 'human:<name>' for a person or 'agent:<name>' for an agent.",
        ) from e
    row = conn.execute(
        "SELECT id, kind, display_name, first_seen_at FROM actor WHERE id = ?",
        (resolved.id,),
    ).fetchone()
    return RegisterOutput(
        actor=ActorRecord(id=row[0], kind=row[1], display_name=row[2], first_seen_at=row[3]),
        created=resolved.created,
    )
