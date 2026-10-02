---
name: local-first-tooling
description: Pick/setup tools under a $0/local-first rule; local LLM agents for routine work, paid APIs only when authorized + spend-guarded.
version: 1.0.1
author: Hermes Agent
platforms: [macos, linux, windows]
---

# Local-first tooling for a cost-sensitive user

Use when evaluating, recommending, installing, or planning any tool/library/integration for Manuel, who enforces a strict **$0 / local** rule: no paid APIs, not even with guardrails (no Haiku alias, no hard_stop, no manual console cap — just don't use it).

## Core rule (workflow discipline)
- **Screen for hidden paid-API dependencies BEFORE proposing.** A tool marketed as "local", "private", or "runs on your machine" may still call a paid LLM for some input types. Verify the free/local boundary, don't trust the tagline.
- **Local-first, not absolute-no-paid.** Default to $0/local. Use a **local LLM agent (Ollama, e.g. `qwen3:8b`)** for routine parsing, classification, and draft generation — this is $0 and the user explicitly wants it used ("haz uso de los agentes locales también", "austeridad de tokens").
- **Paid Claude API is permitted ONLY when BOTH hold:** (a) the user has explicitly authorized it for a specific high-level task (e.g. reconciling a balance that doesn't add up), and (b) it runs with spend guards (low `max_turns`, no long retry loops, manual console cap). It must NOT be used for mechanical/routine work a local model handles.
- **When a cloud integration fails repeatedly, migrate local — don't re-auth.** If a hosted dependency (e.g. Google Drive token revoked repeatedly as `invalid_grant`) blocks the workflow, move it to local-first tooling (Obsidian vault + local git repo) instead of patching the cloud auth. The user chose this decisively: "no dependamos de google drive... hagamoslo en obsidian y la coordinacion la orquestamos con git".
- If the local-only portion is too limited to be useful, say so plainly and let the user choose — do not quietly enable paid mode "just for this one part".
- For knowledge-graph / PKM needs, prefer fully-local options (e.g. Obsidian's native Graph View, a free core feature) over paid-API graph builders.

## Local LLM agent orchestration (token-austerity pattern)
Route mechanical work to a local model and keep the paid model out of the hot path:
1. A local Ollama model parses free-text input into a structured draft (e.g. JSON: libro/tipo/monto/concepto).
2. **Deterministic code (NOT the LLM) performs the actual mutation** (write to xlsx, register a row, etc.).
3. An orchestrator script chains: local-agent parse → deterministic action → rebuild artifact → `git commit`.
4. Always include a non-LLM fallback (regex/heuristic) so the pipeline works if Ollama is down.
Full recipe and working shape in `references/agent-orchestration-local.md`.

## Known cases (pitfalls)
- **Graphify** (`graphifyy` on PyPI): marketed as a local knowledge-graph builder. Reality → code analysis (tree-sitter AST) is 100% local/$0, but extraction from notes / PDFs / **images** uses the Anthropic Claude API (paid). Its headline non-code use case is therefore unusable for a $0 user. Detail in `references/graphify-cost.md`.
- **Obsidian**: fully local desktop app; Graph View is a free core feature. Good $0 alternative for "graficar"/navigate notes.

## Operating the Mac Mini headless (SSH from ThinkPad)
Manuel drives this Mac **headless via SSH from a Linux ThinkPad**. macOS GUI
permission dialogs (System Settings ▸ Privacy ▸ Automation) appear on the
**physical display, not in SSH** — so any tool needing one-time GUI consent
(Mail.app AppleScript, first `osascript`) cannot be approved over SSH and will
hang. Prefer headless CLI tools that need no GUI permission. For sending email
from SSH, use `msmtp` + an app password (not Mail.app). Full recipe, the
local-only `postfix`/`/usr/bin/mail` caveat, the Mail.app Ruta B that WORKS after
a one-time GUI approval, and the Screen-Sharing fallback in
`references/headless-mac-ssh.md`.
**Mail.app via AppleScript IS a valid headless send path once the user approves
the Automation prompt at the physical console** (Ruta B in the reference) — it
delivered to a real Gmail inbox on 2026-08-14. Prefer `msmtp` when no GUI click
is possible; use Mail.app Ruta B when the user can approve the prompt once.

## Setup patterns (this Mac)
- System Python is **3.9.6** and externally-managed: `pip install` is blocked and `uv pip install --system` fails with Permission denied on `/Library/Python/3.9/site-packages`. Use a local venv instead:
  ```
  uv venv .venv && uv pip install <pkg> && uv run python3 <script>
  ```
  (`uv` is installed via `brew install uv` on this machine.)
- Prefer Homebrew for CLI/desktop installs: `brew install <pkg>` / `brew install --cask <app>`.
- macOS cask apps (e.g. Obsidian) must be opened once to register the vault; Hermes reaches the vault via the filesystem, not the app.

## References
- `references/graphify-cost.md` — full Graphify free-vs-paid split and the Obsidian alternative.
- `references/agent-orchestration-local.md` — Ollama JSON-call shape, local-agent→deterministic→build→git orchestrator pattern, and .gitignore/cleanup tricks.
- `references/headless-mac-ssh.md` — running this Mac headless over SSH: GUI permission prompts are unreachable, msmtp email recipe, Mail.app Ruta B (works after one-time GUI approval), postfix caveat, Screen-Sharing fallback, and AppleScript syntax gotchas (`out box` → `-2741`).
