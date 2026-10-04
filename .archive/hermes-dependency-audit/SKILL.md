---
name: hermes-dependency-audit
description: Fix hermes doctor npm vuln findings safely.
---

# Hermes Dependency Audit & Remediation

## When to use
- `hermes doctor` reports lines like "web workspace deps (N high)" or "ui-tui workspace deps (N high)".
- User asks to "fix the vulnerabilities hermes doctor shows" / "resolver las vulnerabilidades".
- You're auditing dependency health of a local hermes-agent repo.

## Key facts (non-obvious)
1. **`hermes doctor` only scans the `web` and `ui-tui` npm workspaces for vulns.** A root-level `npm audit` reveals MORE — electron, tar, mermaid, fast-uri, shell-quote, dompurify in `apps/desktop` and elsewhere — that doctor NEVER mentions. Don't assume doctor's count is the full picture.
2. **Hermes runtime is Python.** The agent you actually run (`~/.local/bin/hermes` → Python) does NOT consume these node_modules. The npm vulns are build-time tooling (eslint, postcss, vite, jsdom, react-router) for the optional web UI / TUI / Electron desktop app, which are usually NOT built or running. Risk is low in practice; cleaning is still good hygiene.
3. **`npm audit fix --force` is dangerous here.** Electron and extract-zip vulns ONLY fix via `--force`, which installs electron@40.x OUTSIDE the declared range and can break the desktop build. Leave these unless the user explicitly wants the desktop app secured.

## Safe remediation workflow
Run from the hermes-agent repo root (typically `~/.hermes/hermes-agent`):

1. Back up the lockfile (it's the single source of truth; web/ui-tui have no lock of their own):
   `cp package-lock.json /tmp/hermes-package-lock.backup.json`
2. Dry-run first to confirm no `package.json` changes:
   `npm audit fix --dry-run`
   (and per-workspace: `npm audit fix --workspace web --dry-run`)
3. Apply in-range fixes per workspace (safe, does NOT edit package.json):
   `npm audit fix --workspace web`
   `npm audit fix --workspace ui-tui`
4. For packages that still flag high but whose `package.json` already allows a patched version via its semver range (e.g. react-router flagged high while `package.json` has `"react-router-dom": "^7.17.0"`), bump the specific package WITHOUT `--force`:
   `npm install react-router-dom@^7.18.2 --workspace web`
   This pulls patched 7.18.2+ that satisfies `^7.17.0`.
5. Apply root-level in-range fix for the rest (mermaid, tar, fast-uri, shell-quote, dompurify, etc. in apps/desktop):
   `npm audit fix`
6. Verify:
   `hermes doctor`  → web/ui-tui lines should now read 0 high
   `npm audit`      → non-force items gone; only electron/extract-zip --force remain

## Pitfalls
- Doctor's vuln count ≠ real count. Always run a root `npm audit` to see the full picture and decide whether to touch the desktop app.
- Never `--force` electron in this repo — it moves outside the declared range and breaks the Electron build.
- If `npm audit fix` errors with an "arborist crash", that's the known npm bug doctor mentions; a lockfile bump clears it — retry after step 3/4.
- React-router in `apps/desktop` may also need the same `^7.18.2` bump; the doctor doesn't report it because it's not in the web/ui-tui scan set.
- A follow-up `npm audit` (days later) can still show `shell-quote` + `concurrently` as HIGH — but fixable WITHOUT `--force` (they re-surface when upstream bumps those transitive deps). Just run `npm audit fix` again to close them. Only `electron` + `extract-zip` truly need `--force`.
- The safe fix leaves 3 files UNCOMMITTED: `apps/desktop/package.json`, `web/package.json`, `package-lock.json`. Decide: commit on a branch or `git checkout -- <files>` to revert — a dirty tree blocks a later `git pull`.
- The repo drifts behind upstream; check `git rev-list --count HEAD..@{u}` before declaring done.
- On macOS `timeout` is NOT installed — run `hermes doctor` / `npm audit` directly, never wrap in `timeout` (it errors "command not found" and the whole line fails).
- See `references/post-fix-followup.md` for the verified follow-up recipe (uncommitted tree, upstream drift, re-surfaced shell-quote/concurrently, macOS timeout gotcha).

## Verification
After fixing, re-run `hermes doctor` and confirm the "web workspace deps" / "ui-tui workspace deps" lines show 0 high. Run `npm audit` at root to confirm the non-force items are gone. The remaining electron/extract-zip items are expected and intentionally left (out-of-range `--force` only).

See `references/audit-session-notes.md` for a concrete reproduction transcript.
