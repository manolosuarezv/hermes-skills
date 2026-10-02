# Local LLM agent orchestration (token-austerity pattern)

When the user wants routine AI work done cheaply, route it through a LOCAL
model (Ollama) and keep the paid API (Claude) out of the hot path. Derived
from the Familia Suárez contabilidad migration (Obsidian vault + local git,
15 AGO 2026) where a flaky Google Drive token was abandoned for local-first.

## Principle
- The LLM only **DRAFTS** (parses free text → structured JSON). Deterministic
  code performs the real mutation (writes a file, registers a row, commits).
- A local Ollama model (e.g. `qwen3:8b`) does parsing/classification for $0.
- Paid Claude API is reserved for high-level tasks the user authorizes, with
  spend guards. See `local-first-tooling` SKILL.md core rule.

## Ollama call shape (enforce JSON)
```bash
curl -s -m 60 http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3:8b","prompt":"<instruction>","stream":false,
       "format":"json","options":{"temperature":0,"num_predict":200}}'
```
- `stream:false` returns `{"response":"..."}`; ignore the `thinking` block.
- `format:"json"` makes qwen emit JSON; still strip ```json fences defensively.
- If Ollama is unavailable, fall back to a regex/heuristic parser (also $0).

## Orchestrator chain (one command, end-to-end)
1. `agente_local.py "<free text>"` → parses to a JSON draft (libro/tipo/monto/concepto).
2. Deterministic `registrar_local.py` performs the action (no cloud upload).
3. `build.py` regenerates the derived artifact (e.g. a markdown summary note
   written into the Obsidian vault).
4. `commit.sh` runs `git add -A && git commit` in the local repo.

## .gitignore for the local repo (private, no remote)
Exclude: credentials/tokens (`drive_token.json`, `*.token.json`, `.env`),
`venv/`, `__pycache__`, `*.bak*` backups, `**/*.pdf`, and debug scripts
(`scripts/_*.py`). NEVER version tokens — even in a local-only repo.

## Caveats / reusable tricks
- `git check-ignore` on Apple Git (2.50.x) can return exit 1 for files that
  ARE ignored when the path contains spaces; confirm with `git status --short`
  instead of trusting `check-ignore` alone.
- A local git repo with no remote: a bad first commit containing secrets/backups
  can be fully erased by `rm -rf .git && git init` (safe when there is no remote
  and physical files are untouched) — prefer this over messy `rebase -i` cleanup.
- To verify a migration end-to-end without leaving trace: back up the real data
  file to `tempfile`, run the pipeline with `--no-commit`, assert the row count
  changed, then `shutil.copy` the backup back; finally `git checkout --` any
  regenerated artifacts and delete the temp verify script.
