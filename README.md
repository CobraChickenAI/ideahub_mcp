# <span data-proof="authored" data-by="ai:claude">ideahub-mcp</span>

<span data-proof="authored" data-by="ai:claude">An agent-first MCP server for capturing and recalling ideas — the agent's and their human's.</span>

<span data-proof="authored" data-by="ai:claude">The primary user is a model. See</span> <span data-proof="authored" data-by="ai:claude">`docs/design.md`</span> <span data-proof="authored" data-by="ai:claude">for principles.</span>

## <span data-proof="authored" data-by="ai:claude">Usage</span>

```bash proof:W3sidHlwZSI6InByb29mQXV0aG9yZWQiLCJmcm9tIjowLCJ0byI6MTgsImF0dHJzIjp7ImJ5IjoiYWk6Y2xhdWRlIn19XQ==
uv run ideahub-mcp
```

<span data-proof="authored" data-by="ai:claude">Configured via environment:</span>

* <span data-proof="authored" data-by="ai:claude">`IDEAHUB_MCP_HOME`</span> <span data-proof="authored" data-by="ai:claude">— data directory (default</span> <span data-proof="authored" data-by="ai:claude">`~/.ideahub-mcp/`)</span>

* <span data-proof="authored" data-by="ai:claude">`IDEAHUB_ACTOR`</span> <span data-proof="authored" data-by="ai:claude">— actor fallback (e.g.</span> <span data-proof="authored" data-by="ai:claude">`human:michael`)</span>

* <span data-proof="authored" data-by="ai:claude">`IDEAHUB_SCOPE`</span> <span data-proof="authored" data-by="ai:claude">— scope fallback (e.g.</span> <span data-proof="authored" data-by="ai:claude">`global`)</span>