# Post-fix follow-up: what the initial safe fix leaves behind

Verified 2026-08-25 on macOS after running the safe remediation workflow from SKILL.md.

## The fix leaves uncommitted local changes
After `npm audit fix --workspace web` / `--workspace ui-tui` / root `npm audit fix`
plus the react-router bumps, `git status` shows (uncommitted):
  M apps/desktop/package.json
  M web/package.json
  M package-lock.json
Decide: commit on a branch, or `git checkout -- <files>` to revert. A dirty tree
blocks a later `git pull` and the changes are easy to lose track of.

## Repo can be behind upstream
`git rev-list --count HEAD..@{u}` may report commits behind (e.g. 1 — often a
docs/skill commit, low risk). Check before declaring "done". Re-running the fix
is non-destructive to your own config.

## A follow-up `npm audit` still shows 4 high (not just 2)
The original session notes claimed only electron + extract-zip remained. A later
`npm audit` showed 4 high, all dev/build tooling:
  1. electron     — high, needs --force (outside range) → leave
  2. extract-zip  — high, needs --force → leave
  3. shell-quote <=1.8.4        — high, DoS in parse(); FIXABLE WITHOUT --force
  4. concurrently 9.2.1-9.2.3 || 10.0.0-10.0.3 — high, pulls vulnerable shell-quote; FIXABLE WITHOUT --force
`npm audit fix --dry-run` confirms shell-quote/concurrently are in-range fixable.
Run `npm audit fix` AGAIN to close them. Only electron + extract-zip truly need --force.

## macOS note
`timeout` is NOT installed on macOS — run `hermes doctor` / `npm audit` directly,
without wrapping in `timeout` (it errors with "command not found" and the whole
command line fails).
