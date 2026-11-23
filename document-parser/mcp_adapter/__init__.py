"""MCP document server — the agent-facing driving adapter.

The SDK is imported when a server is built, not when this package is: a
backend with MCP_ENABLED off never loads it.

The package is named `mcp_adapter`, not `mcp`, because a top-level `mcp`
package in the backend root would shadow the SDK on `sys.path`.
"""
