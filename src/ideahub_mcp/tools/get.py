from __future__ import annotations

import json
import sqlite3

from pydantic import BaseModel

from ideahub_mcp.errors import IdeaHubError


class GetInput(BaseModel):
    id: str


class NoteOut(BaseModel):
    id: str
    kind: str | None
    content: str
    actor: str
    originator: str | None
    created_at: str


class LinkOut(BaseModel):
    target_idea_id: str
    kind: str


class GetOutput(BaseModel):
    id: str
    content: str
    scope: str
    actor: str
    originator: str | None
    tags: list[str]
    created_at: str
    archived_at: str | None
    notes: list[NoteOut]
    links: list[LinkOut]


def get_idea(conn: sqlite3.Connection, input_: GetInput) -> GetOutput:
    row = conn.execute(
        "SELECT id, content, scope, actor_id, originator_id, tags, created_at, archived_at "
        "FROM idea WHERE id = ?",
        (input_.id,),
    ).fetchone()
    if not row:
        raise IdeaHubError(
            code="idea_not_found",
            message=f"No idea with id={input_.id}",
            fix="Call list_ideas or dump_ideas to discover valid ids.",
        )
    notes = [
        NoteOut(id=r[0], kind=r[1], content=r[2], actor=r[3], originator=r[4], created_at=r[5])
        for r in conn.execute(
            "SELECT id, kind, content, actor_id, originator_id, created_at "
            "FROM idea_note WHERE idea_id = ? ORDER BY created_at DESC",
            (input_.id,),
        ).fetchall()
    ]
    links = [
        LinkOut(target_idea_id=r[0], kind=r[1])
        for r in conn.execute(
            "SELECT target_idea_id, kind FROM idea_link WHERE source_idea_id = ?",
            (input_.id,),
        ).fetchall()
    ]
    return GetOutput(
        id=row[0],
        content=row[1],
        scope=row[2],
        actor=row[3],
        originator=row[4],
        tags=json.loads(row[5]),
        created_at=row[6],
        archived_at=row[7],
        notes=notes,
        links=links,
    )
