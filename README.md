# <span data-proof="authored" data-by="ai:claude">ideahub-mcp</span>

An agent-first [MCP](https://modelcontextprotocol.io) server for capturing and recalling ideas — the agent's and their human's.

The primary user is a model. Tools are short, imperative, example-laden; errors carry a repair path; scope and actor resolve from context so the agent doesn't have to ask.

## Tools

| Tool         | Purpose                                                                                 |
| ------------ | --------------------------------------------------------------------------------------- |
| `capture`    | Durable idea. Use when work produces something worth preserving beyond the task.        |
| `checkpoint` | Lightweight working-memory trace. Use mid-task for observations, decisions, next steps. |
| `dump`       | Text-blob summary of the scoped corpus under a token budget.                            |
| `search`     | FTS5 + bm25 ranked search with snippets.                                                |
| `list`       | Filter ideas by scope, actor, tags, date range.                                         |
| `get`        | Full detail for one idea, with notes and outbound links.                                |
| `related`    | Nearest neighbors by tag overlap → shared originator → recency.                         |
| `annotate`   | Append a free-text note to an idea without mutating it.                                 |
| `archive`    | Hide an idea; write a typed `archive` note with reason.                                 |
| `link`       | Connect two ideas (`related`, `supersedes`, `evolved_from`, `duplicate`).               |
| `recognize`  | Inspect the actor table.                                                                |
| `ping`       | Cheap no-side-effect health probe for connection/debugging.                             |

## Writeback Loop

`ideahub-mcp` is designed to behave like working memory for an agent, not just searchable storage. Two write verbs close that loop:

- `capture` writes a durable idea that should survive the task.
- `checkpoint` writes a lightweight in-flight trace — observations, decisions, assumptions, open questions — without the semantic weight of a full idea.

All write-path verbs (`capture`, `checkpoint`, `annotate`, `link`) accept an optional `task_ref` — an opaque free-form string that groups every write from the same task so the stream can be reconstructed later.

`capture` and `checkpoint` return scored `annotate_candidates` and `related_candidates` in their response so the model sees where a fresh trace probably belongs (usually as an annotation on an existing idea) without having to search. Checkpoints are default-excluded from `search`, `list`, and `dump` so cheap traces do not bleed into orientation surfaces — opt in with `include_checkpoints=True`.

## Discovery And Health

`ideahub-mcp` is intentionally tool-first, not resource-first. A client may show a
healthy connection even when `list_resources()` is sparse or empty.

To make discovery cheap and host-agnostic, the server exposes:

- `ping`: a no-side-effect tool for "is the server connected and responsive?"
- `ideahub://status`: a status resource that reports package version, storage paths,
  and the current tool surface

That design supports hosts that favor different MCP surfaces. Some clients reason
primarily over tools. Others probe resources first. A healthy server should be easy
to verify in either style.

For the full compatibility rubric, see [docs/mcp-health.md](docs/mcp-health.md).

## Install

```bash
uvx ideahub-mcp        # try it
uv tool install ideahub-mcp   # keep it around
```

## Claude Code

Add to `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "ideahub": {
      "command": "uvx",
      "args": ["ideahub-mcp"],
      "env": {
        "IDEAHUB_MCP_HOME": "/Users/you/.ideahub-mcp",
        "IDEAHUB_ACTOR": "human:you"
      }
    }
  }
}
```

## Configuration

| Var                                                                       | Default                                                                  | Purpose                                          |
| ------------------------------------------------------------------------- | ------------------------------------------------------------------------ | ------------------------------------------------ |
| <span data-proof="authored" data-by="ai:claude">`IDEAHUB_MCP_HOME`</span> | <span data-proof="authored" data-by="ai:claude">`~/.ideahub-mcp/`</span> | Data directory (SQLite store, logs, backups).    |
| <span data-proof="authored" data-by="ai:claude">`IDEAHUB_ACTOR`</span>    | —                                                                        | Fallback actor id (`human:you` or `agent:name`). |
| <span data-proof="authored" data-by="ai:claude">`IDEAHUB_SCOPE`</span>    | —                                                                        | Fallback scope when cwd isn't a git repo.        |

Actor resolution: explicit arg → MCP `clientInfo.name` → `IDEAHUB_ACTOR` → error.
Scope resolution: explicit arg → `IDEAHUB_SCOPE` → `repo:<git-toplevel>` → <span data-proof="authored" data-by="ai:claude">`global`</span>.

## Storage

One SQLite file with WAL, FTS5, and hand-rolled migrations. No ORM. Daily snapshots to `$IDEAHUB_MCP_HOME/backups/` with 14-day retention.

## Develop

```bash
uv sync --dev
uv run pytest
uv run ruff check .
uv run pyright
```

## License

MIT.
