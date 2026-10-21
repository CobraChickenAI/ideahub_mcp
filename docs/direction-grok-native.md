# Direction: IdeaHub as the foundation for Grok Native

Status: working direction, not a release plan. Last updated Oct 21, 2026.

## Summary

`ideahub_mcp` is the foundation service for a set of AI agents that work for one
person, Michael Schartung. The working name for the service built on it is
**Grok Native**. Grok Native carries the IdeaHub concept as it already exists in
this package. It does not replace it.

The intended role: one shared, owned source of truth. Many agents read from it.
One writer appends to it.

## What carries over from IdeaHub

Nothing new is invented here. The direction relies on what the package already
does:

- **capture / checkpoint / promote.** Durable ideas, lightweight in-task traces,
  and a one-way promotion from trace to idea that keeps the id, links, and notes.
- **Append-only store.** Ideas are not edited in place. Changes arrive as notes
  (`annotate`), archive records with a reason (`archive`), or new ideas linked to
  old ones.
- **Typed links.** `related`, `duplicate`, `evolved_from`, `supersedes`. A changed
  position is a new idea that `supersedes` the old one, so the dated history stays.
- **Actors and originators.** Every row records who wrote it (`actor`) and, when it
  differs, whose thought it was (`originator`). With the fixes in this branch, a
  configured `IDEAHUB_ACTOR` wins over the client name, and `register` adds a person
  as an actor without a side-effect write.

## Why a single source of truth

When the same position lives in several agent configs, the copies drift apart. One
agent keeps repeating an old version after the person has changed their mind. A
single append-only store with `supersedes` links gives every agent the same current
answer and keeps the history of how it changed.

## Shape

- **Readers:** any number of agents, through MCP (`search`, `list`, `get`,
  `related`, `dump`).
- **Writer:** one process per store. Today that is an ingester that runs outside
  this package (see [sidecars.md](sidecars.md)). Agents hand material to it through
  files; they do not write to the store themselves.
- **Provenance:** every entry carries actor, originator, timestamps, tags, and links.
  The aim is to show who said what, and when, from the store alone.

## Scope decisions

- **The rework stands.** Rebuilding IdeaHub as Michael's own foundation, starting
  as shared memory for his agents, is the current direction. A work version could
  be built on the same base later.
- **Out of scope: the "staking claim".** On Oct 18, 2026 the idea of using this
  work as a dated public stake that he did it first was dropped. It is not part of
  this direction and should not be added back. The project's provenance is already
  in its own commit history and release records.
- **Out of scope: multi-writer safety.** Several processes writing to one store at
  once needs its own design. Until then, the rule is one writer per store.

## Open questions

- **Hosting.** The server runs locally over stdio. Agents on other machines need
  a hosted transport.
- **Read-before-answer.** Nothing makes an agent consult the store before it states
  a position. That belongs to the agent setup, not to this package.
- **Ownership.** There is no field for which agent owns a position. Tags can stand
  in for one, but nothing enforces them.
