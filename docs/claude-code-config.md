# <span data-proof="authored" data-by="ai:claude">Claude Code Configuration</span>

<span data-proof="authored" data-by="ai:claude">Add to</span> <span data-proof="authored" data-by="ai:claude">`~/.claude/settings.json`</span> <span data-proof="authored" data-by="ai:claude">under</span> <span data-proof="authored" data-by="ai:claude">`mcpServers`:</span>

```json proof:W3sidHlwZSI6InByb29mQXV0aG9yZWQiLCJmcm9tIjowLCJ0byI6MjcyLCJhdHRycyI6eyJieSI6ImFpOmNsYXVkZSJ9fV0=
{
  "mcpServers": {
    "ideahub": {
      "command": "uv",
      "args": ["--directory", "/Users/you/Cowork/ideahub-mcp", "run", "ideahub-mcp"],
      "env": {
        "IDEAHUB_MCP_HOME": "/Users/you/.ideahub-mcp",
        "IDEAHUB_ACTOR": "human:you"
      }
    }
  }
}
```