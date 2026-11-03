# Docling Studio for Claude

This plugin connects Claude to the MCP server of your own
[Docling Studio](https://github.com/scub-france/Docling-Studio), so Claude can
answer from the documents you parsed there. It works without chunks or
embeddings (Chunkless RAG): Claude finds a document, reads its map, opens only
the sections the question needs, and backs every claim with a quote that the
server checks against the document.

## Before you install

- Docling Studio runs on your machine or your network, version 0.7.3 or later.
- Its MCP server is on: **Settings → MCP server** shows *On*.

## Install

In Claude Code:

```
/plugin marketplace add scub-france/Docling-Studio
/plugin install docling-studio@docling-studio
```

Claude Code asks for the MCP URL of your Studio:

| How Studio runs | URL |
|-----------------|-----|
| Docker Compose | `http://localhost:3000/mcp` (the default) |
| From source | `http://localhost:8000/mcp` |

Change it later in `/config`. If you added the server by hand before
(`claude mcp add ... docling-studio`), remove that entry with
`claude mcp remove docling-studio`, or Claude sees every tool twice.

## What you get

- `find_documents`, `get_outline`, `read_element`, `verify_citation`: find a
  document, read its map, read a section under a token budget, check a quote.
- `show_sources`: a card that shows where the answer came from, page by page,
  on hosts that display MCP Apps.
- The `chunkless_rag` prompt, which runs the whole loop for one question.

Every tool only reads. None of them changes a document or an analysis.

## What it connects to

The plugin runs nothing on your machine and contains no code. It declares one
MCP server, at the URL you give, and sends it nothing but the tool calls
Claude makes. Your files and your Studio database stay where Studio runs. The
passages Claude reads through these tools become part of your conversation
with Claude, like any text you share with it.

Studio's MCP server has no authentication: anyone who can reach `/mcp` can
read every document. Keep that port on your machine or a trusted network. See
[the MCP server documentation](https://scub-france.github.io/Docling-Studio/mcp-server/)
for the details and the other ways to connect a client.

## License

MIT, like Docling Studio.
