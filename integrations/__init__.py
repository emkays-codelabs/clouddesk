"""Outside-world adapters: protocols, in-memory mocks, a factory and the read-only MCP server.

Does: define what the support tools may ask of email, billing, workspace admin and ticket
notification, and supply mock adapters that record calls. Must NOT: send real email or move real
money (v1 non-goal), be imported by `backend/app/core` (tests enforce it), or call an LLM.
"""
