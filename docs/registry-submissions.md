# Registry submission drafts

These are drafted but NOT submitted. Submit after polishing is done.

## 1. modelcontextprotocol/servers

Submit as a PR to https://github.com/modelcontextprotocol/servers — adds one line to the "Community Servers" section of `README.md`, alphabetically.

**Line to add:**

```markdown
- [ideahub-mcp](https://github.com/CobraChickenAI/ideahub-mcp) - Agent-first idea capture and recall with FTS5 search, scope/actor resolution, and idempotent writes.
```

**PR title:** `Add ideahub-mcp to community servers`

**PR body:**

```
Adds ideahub-mcp, an agent-first MCP server for capturing and recalling ideas.

Ten tools over a single SQLite store: capture, dump, search, list, get, related, annotate, archive, link, recognize. Built for the model as primary user — tool descriptions are prompts, errors carry a repair path, scope and actor resolve from MCP clientInfo + cwd without asking.

- Repo: https://github.com/CobraChickenAI/ideahub-mcp
- PyPI: https://pypi.org/project/ideahub-mcp/
- Install: `uvx ideahub-mcp`
- License: MIT
```

## 2. Smithery

Submit via the web UI at https://smithery.ai/new (requires GitHub sign-in as a CobraChickenAI member).

**Fields:**

- **Repository**: `CobraChickenAI/ideahub-mcp`
- **Display name**: `ideahub-mcp`
- **Tagline**: `Agent-first idea capture and recall.`
- **Category**: `Productivity` (or `Memory`, if they have it)
- **Install command**: `uvx ideahub-mcp`
- **Config schema**: point at the env vars (`IDEAHUB_MCP_HOME`, `IDEAHUB_ACTOR`, `IDEAHUB_SCOPE`) — Smithery may auto-detect from a `smithery.yaml` if present.

If Smithery requires a `smithery.yaml`, drop this at repo root:

```yaml
startCommand:
  type: stdio
  command: uvx
  args: [ideahub-mcp]
  env:
    IDEAHUB_MCP_HOME: ${IDEAHUB_MCP_HOME}
    IDEAHUB_ACTOR: ${IDEAHUB_ACTOR}
    IDEAHUB_SCOPE: ${IDEAHUB_SCOPE}
```

## 3. mcp-get (optional)

`mcp-get` is a community CLI registry: https://github.com/michaellatman/mcp-get. Submission is also a PR adding one entry to `packages/package-list.json`:

```json
{
  "name": "ideahub-mcp",
  "description": "Agent-first idea capture and recall with FTS5 search.",
  "vendor": "CobraChickenAI",
  "sourceUrl": "https://github.com/CobraChickenAI/ideahub-mcp",
  "homepage": "https://github.com/CobraChickenAI/ideahub-mcp",
  "license": "MIT",
  "runtime": "python"
}
```

## Order

1. Finish polishing/refinement.
2. Consider cutting v0.1.1 with polish fixes.
3. Submit modelcontextprotocol/servers PR first — highest-signal surface.
4. Smithery next — lowest friction, good for humans discovering via web.
5. mcp-get last — nice-to-have.
