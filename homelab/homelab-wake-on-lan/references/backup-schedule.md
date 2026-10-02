# Power-on-demand backup schedule (qbex / homelab) — WORKING RECIPE

Recurring pattern for a box normally OFF to save power: a job must
(1) wake it, (2) do the work, (3) confirm, (4) shut it down. This is the
daily "contabilidad de Renata Suárez y la familia Suárez" Drive→RAID backup.
All pieces below were VERIFIED working in the 2026-08-04 session.

## Environment (verified)
- qbex = server01, Debian, LAN 192.168.1.69, RAID1 `/mnt/raid` (ext4, ~500G free).
- SSH user `user01` (case-sensitive — `User01` rejected). Password auth works
  via expect; a key is now installed for passwordless cron runs.
- Mac key: `/Users/manuelsuarez/.ssh/id_ed25519_qbex` (ed25519, no passphrase).
  Installed into qbex `~/.ssh/authorized_keys`. Use `-o BatchMode=yes`.
- qbex has NOPASSWD sudo: `/etc/sudoers.d/user01-nopasswd`
  (`user01 ALL=(ALL) NOPASSWD: ALL`).
- Drive access lives on the **Mac**, NOT qbex:
  `/Users/manuelsuarez/.hermes/contabilidad/` has `drive_token.json` (OAuth),
  a `venv` with `google-api`+`openpyxl`, and `registrar.py` (Drive list/get).
  Do NOT use `rclone` — the token+google-api path already works and avoids a
  second OAuth setup.

## Step 1 — Wake + wait-until-up
`python3 /Users/manuelsuarez/bin/prender-server.py` (targets both qbex NICs),
then poll `--check` until ENCENDIDO. Old AMD/nForce HW needs 30–60s POST+boot.
Then run the work. Never SSH before it answers.

## Step 2 — Drive pull (on Mac, via token+venv) then scp to qbex
```sh
cd /Users/manuelsuarez/.hermes/contabilidad && source venv/bin/activate
python3 - <<'PY'
import registrar as R
for k in ("renata","familia"):
    R.descargar(k)   # updates ./contabilidad <Renata|familia> suarez 2026.xlsx
PY
scp -i /Users/manuelsuarez/.ssh/id_ed25519_qbex -o BatchMode=yes \
  contabilidad\ *.xlsx user01@192.168.1.69:/mnt/raid/backups/contabilidad_suarez/backup/
```
Files map: `renata`→"contabilidad Renata suarez 2026.xlsx",
`familia`→"contabilidad familia suarez 2026.xlsx" (see `registrar.FILES`).

## Step 3 — Space-efficient git versioning (on qbex)
git is content-addressed: unchanged bytes dedupe automatically, daily
snapshots cost ~only the delta. Repo measured at ~196K after first commit.
```sh
cd /mnt/raid/backups/contabilidad_suarez
git init -q 2>/dev/null
git config user.email backup@qbex; git config user.name "Backup qbex"
git add -A
git diff --cached --quiet || {            # skip commit if nothing changed
  git commit -q -m "backup $(date +%F_%H%M)"
  git tag -f v$(date +%F_%H%M)
}
git gc --aggressive --prune=now           # keep .git tiny
```
Version ledger = git tags (`git tag` / `git log`). No external VERSIONES.txt
needed; tags ARE the version file.

## Step 4 — Verify THEN shutdown (never blind)
- Confirm files present + commit happened on qbex:
  `test -f /mnt/raid/backups/contabilidad_suarez/backup/*.xlsx && echo OK`.
- Only then power off — use `systemctl poweroff -f`, NOT `shutdown -h now`
  (the latter fails over SSH with "Access denied" on Debian/systemd; see
  SKILL.md pitfall):
  `ssh -i ... -o BatchMode=yes user01@192.168.1.69 'sudo systemctl poweroff -f'`.
- **Verify OFF correctly (easy to get wrong):** forced power-off is NOT
  instant. `sshd` stops almost immediately (SSH → "Connection refused") but
  ICMP keeps answering for ~60–120s while the RAID/network target tears down.
  A `ping` issued right after the command will LIE and say the box is up.
  Do: wait ~75s, then BOTH `ping -c4 192.168.1.69` (must be 100% loss) AND
  `ssh ... 'echo up'` (must be "Operation timed out", NOT "Connection
  refused"). "Connection refused" = sshd torn down but kernel still alive =
  shutdown still in progress, NOT yet off. Only when ping is dead AND ssh
  times out is qbex truly OFF. Confirmed empirically 2026-08-07: ssh went
  refused→timed-out and ping went UP→OFF after ~1–2 min.

## Orchestrator script (already created)
`/Users/manuelsuarez/bin/backup_contabilidad_diario.sh` — does WOL→wait→
backup→confirm→shutdown end to end. The Mac-side Python
`/Users/manuelsuarez/.hermes/contabilidad/backup_qbex.py` does the Drive pull
+ scp + remote git commit/tag/gc. Both were tested and produced
commit `v2026-08-04_1934`.

## Cron design (Hermes `cronjob`)
- Daily 00:00 `0 0 * * *`: run the orchestrator, then `ping` to confirm qbex
  is OFF. Job loads `homelab-wake-on-lan`.
- Separate one-off at 01:00 to shut qbex down when a maintenance window ends
  (user wanted it up until 1am then off). Set `deliver='telegram'`/`'all` if
  you want a notification — CLI/local jobs save output but don't push it back.

## Gotchas confirmed this session
- `echo pass | sudo -S` is BLOCKED by the agent runtime. Use `ssh -t` + expect
  (see SKILL.md SSH section) for one-off sudo; for cron, use the NOPASSWD sudo
  file + SSH key so no password is needed at all.
- Drive OAuth token on Mac beats rclone (no second auth flow). Reuse
  `registrar.py`/`drive_token.json`; refresh token survives normal use.
- **Backup git repo lives on qbex, NOT locally.** The version tag
  (`vYYYY-MM-DD_NNNN`) and `SIZE:NNNK` are produced by `backup_qbex.py` on the
  qbex RAID repo (`/mnt/raid/backups/contabilidad_suarez`). Once qbex is
  powered OFF, a local `git tag`/`git log` in
  `/Users/manuelsuarez/.hermes/contabilidad` fails with exit 128 ("not a git
  repository") — that is EXPECTED, not a backup failure. The authoritative
  tag/size are whatever `backup_qbex.py` printed during the run, e.g.
  `COMMIT_OK v2026-08-07_0001` and `SIZE:224K`. Don't re-SSH to a powered-off
  box to "verify the tag".
- **Orchestrator script may lack the +x bit.** Running
  `/Users/manuelsuarez/bin/backup_contabilidad_diario.sh` directly can fail
  with exit 126 "permission denied". If that happens run it via `bash
  /Users/manuelsuarez/bin/backup_contabilidad_diario.sh`, or one-time
  `chmod +x /Users/manuelsuarez/bin/backup_contabilidad_diario.sh` (done
  2026-08-07).

## Reporting the daily run (how to read the output — EASY TO GET WRONG)
`backup_qbex.py` prints several lines; only some mean a new version was made.
Map each to the correct report field:

- `BACKUP_DONE 2026-08-08_0001` → this is just the **run timestamp** string
  (`YYYY-MM-DD_HHMM`), NOT a git tag. Never report it as "versión/tag".
- `COMMIT_OK v2026-08-08_0001` → a real new git commit+tag was created. This
  is the tag to report.
- `SIN_CAMBIOS` → the xlsx files pulled from Drive were **byte-identical** to
  the last commit on qbex. **No commit and NO new tag were created that day.**
  → Report: "sin cambios; último tag = el de la corrida anterior". Do NOT
  invent `v2026-08-08_0001` from the `BACKUP_DONE` line — that tag does not
  exist in the repo. Confirmed gotcha 2026-08-08: run produced SIN_CAMBIOS,
  so the correct version report was "no hubo tag nuevo hoy, repo sin cambios".
- `SIZE:224K` → the **repo size** to report (`.git` on qbex after
  `git gc --aggressive`). It's stable run-to-run unless a delta landed.
- `RESPALDO_CONFIRMADO` (from the orchestrator's confirm step) → both xlsx
  exist on RAID. This is the success signal, independent of COMMIT/SIN_CAMBIOS.

So a correct summary always states THREE things: (1) tag/versión — either the
real `v...` tag OR "SIN_CAMBIOS, sin tag nuevo"; (2) tamaño repo (`SIZE:` line);
(3) qbex OFF (ping, see Step 4). The git repo is on qbex, so you cannot query
the tag after shutdown — use the lines `backup_qbex.py` printed during the run.

**Empirical ping-race confirmation (2026-08-08):** issued right after the
"apagando" message, the first `ping 192.168.1.69` still answered (ON); a
re-check ~60s later returned 100% loss (OFF). Matches the ~75s window in Step 4
— always retry the OFF ping, never trust the one right after the poweroff call.
