from __future__ import annotations

import sqlite3

from pydantic import BaseModel


class SearchInput(BaseModel):
    query: str
    scope: str | None = None
    since: str | None = None
    limit: int = 25
    include_archived: bool = False


class SearchHit(BaseModel):
    id: str
    scope: str
    actor: str
    snippet: str
    score: float
    created_at: str


class SearchOutput(BaseModel):
    hits: list[SearchHit]
    count: int
    query: str


def search_ideas(conn: sqlite3.Connection, input_: SearchInput) -> SearchOutput:
    where = ["idea_fts MATCH ?"]
    params: list[object] = [input_.query]
    if input_.scope:
        where.append("i.scope = ?")
        params.append(input_.scope)
    if input_.since:
        where.append("i.created_at >= ?")
        params.append(input_.since)
    if not input_.include_archived:
        where.append("i.archived_at IS NULL")

    sql = (
        "SELECT i.id, i.scope, i.actor_id, "
        "       snippet(idea_fts, 0, '[', ']', '…', 10) AS snip, "
        "       bm25(idea_fts) AS score, "
        "       i.created_at "
        "FROM idea_fts JOIN idea i ON i.rowid = idea_fts.rowid "
        f"WHERE {' AND '.join(where)} "
        "ORDER BY score ASC "
        "LIMIT ?"
    )
    params.append(input_.limit)
    rows = conn.execute(sql, params).fetchall()
    hits = [
        SearchHit(
            id=r[0],
            scope=r[1],
            actor=r[2],
            snippet=r[3],
            score=float(r[4]),
            created_at=r[5],
        )
        for r in rows
    ]
    return SearchOutput(hits=hits, count=len(hits), query=input_.query)
