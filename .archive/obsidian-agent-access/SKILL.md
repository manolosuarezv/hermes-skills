---
name: obsidian-agent-access
description: "Connect an AI agent to an Obsidian vault with tiered access."
version: 1.0.0
author: Nous Research (curated from session 2026-08-09)
license: Proprietary
platforms: [macos, linux, windows]
metadata:
  hermes:
    tags: [obsidian, agent, privacy, access-control, git, knowledge-base]
    category: note-taking
    related_skills: [obsidian]
---

# Obsidian + Agent Secure Access

Connect an AI agent to an Obsidian vault without exposing the user's private data.
This is the agent-integration counterpart to the `obsidian` skill (which is
filesystem-only). Trigger whenever an agent will read and/or write notes in a user's
vault, especially when the vault contains sensitive material (journal, finances,
strategy).

Adapted from the Wanderloots "secure Obsidian + Hermes" pattern, simplified for a
local agent (no Docker required).

## Core model: 3 folder tiers

Isolate by filesystem layout, not by per-call checks:

- `00 Private/`      → agent has NO access (journal, strategy, secrets).
- `10 Read-Only/`    → agent may read, never write (reference material, legal docs).
- `20 Read-Write/`   → agent may read + write (projects, MOC, plantillas).

Enforce the policy in `~/.hermes/.env` with `OBSIDIAN_VAULT_PATH` plus an explicit
comment block listing the grants. Example:

    OBSIDIAN_VAULT_PATH=~/Obsidian
    # 00 Private/             -> NO agent access, except:
    # 00 Private/Contabilidad/ -> READ+WRITE (granted by user)
    # 10 Read-Only/           -> read only
    # 20 Read-Write/          -> read + write

A documented exception (e.g. a contabilidad subfolder) lives under `00 Private/` with
its own explicit RW grant. The rest of `00 Private/` stays off-limits.

## Access masking without Docker

Wanderloots uses Docker bind mounts to make folders invisible to the agent. On a local
Mac Mini / Linux box where the agent already runs locally, replicate the same isolation
simply by restricting which folders the agent may index/edit. No container, no extra
cost. Keep source-of-truth sensitive data (e.g. `.xlsx` accounting books) OUTSIDE the
vault; mirror only human-readable notes into the private tier.

## Git as the undo button (MANDATORY before any agent write)

1. `git init` the vault.
2. `.gitignore`: `.obsidian/workspace.json`, `.obsidian/workspace-mobile.json`, `.trash/`.
3. Add two remotes, reusing any existing backup script the user has:
   - server: `ssh user@host 'git init --bare /path/repo.git'` → `git remote add server ssh://user@host/path/repo.git`
   - iCloud Drive: bare repo at `~/Library/Mobile Documents/com~apple~CloudDocs/<name>.git` → `git remote add icloud <that path>`
   (Paths with spaces must be quoted in shell commands.)
4. `git add -A && git commit -m "init"` then `git push -u server master && git push -u icloud master`.

A botched agent edit is reverted with `git checkout` / `git reset`; the two remotes are
off-box backups.

## Prioritize one working workflow first

When asked to wire several projects into the vault, build and validate the most
sensitive one end-to-end first (e.g. contabilidad), then extend to the rest under
`20 Read-Write/`. Confirm with a smoke test before declaring success.

## Smoke test

1. Agent `write_file` into a RW tier → note appears in Obsidian graph.
2. Agent `write_file` into `00 Private/` (non-granted folder) → MUST be refused by policy.
3. `git add -A && git commit && git push server && git push icloud` → both succeed.
4. `git checkout` reverts a test change (proves the undo button).

## Librarian / LLM-Wiki (future)

Keep a `20 Read-Write/INDEX.md` MOC of `[[wikilinks]]`. Surface private indices by
*wikilink only*, never by dumping private content into shared notes.

## Pitfalls

- Don't move source-of-truth files (xlsx, credentials) into the vault; mirror notes.
- Don't make the agent's write scope broader than the tier policy comment states.
- iCloud Drive paths contain spaces — always quote them in shell/`git` commands.
- Verify the `.env` path resolves: `echo "${OBSIDIAN_VAULT_PATH/#\~/$HOME}"`.

## References

- `references/macos-recalc-and-localized-dates.md` — macOS `recalc.py` Python<3.10
  failure + soffice workaround, and a stdlib es_CO datetime parser for Trii/bank exports.
