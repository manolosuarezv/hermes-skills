# Graphify — free/local vs paid API split

Source: `https://github.com/Graphify-Labs/graphify` README (Aug 2026).

## What it is
CLI in Python (PyPI package `graphifyy`; the CLI/skill command is still `graphify`).
Builds a knowledge graph from a folder (code, docs, PDFs, images, videos).
Output: `graphify-out/` with `graph.html` (interactive viz), `GRAPH_REPORT.md`,
`graph.json`, `obsidian/` (opens as an Obsidian vault), `wiki/` (with `--wiki`), etc.
Tech: NetworkX + Leiden (graspologic) + tree-sitter + Claude + vis.js. No Neo4j, no server.

## The paid boundary (critical)
- **Code analysis (`.py .ts .js .go .rs .java .c .cpp .rb .cs .kt .scala .php`)** → AST via
  tree-sitter + call-graph pass. **100% local, $0.** No LLM.
- **Docs (`.md .txt .rst`)** → "Concepts + relationships via Claude" → **PAID API (Anthropic)**.
- **Papers (`.pdf`)** → citation mining + concept extraction → **PAID API (Anthropic)**.
- **Images (`.png .jpg .webp .gif`)** → "Claude vision" → **PAID API (Anthropic)**.
- **Videos/audio** → faster-whisper + yt-dlp (local) but then graph edges likely via Claude.

Edges are tagged EXTRACTED / INFERRED / AMBIGUOUS. Many "surprising connection" features
depend on the LLM pass, so the interesting non-code value is unavailable without the API.

## Why it was rejected (this user)
Manuel enforces strict $0/local. Graphify's headline use case (drop in notes/PDFs/images,
get a graph) is exactly the LLM-paid path. Using ONLY the code-AST path defeats the purpose
of a note/knowledge graph. Decision: drop entirely; use Obsidian's native Graph View ($0 core).

## Install notes (for reference, not recommended here)
Requires Python 3.10+. On this Mac (3.9.6 externally-managed) you'd need uv/pyenv for a
3.10+ interpreter. `pip install graphifyy && graphify install` registers a Claude Code skill.
macOS externally-managed fix: `pipx install graphifyy` (handles PATH) or a uv venv.
