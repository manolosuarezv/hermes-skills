---
name: qbex-contabilidad-backup
description: Run or fix the daily qbex contabilidad backup to RAID.
---

# qbex Contabilidad Backup

## When to use
- User asks to "run the daily contabilidad backup", "backup de contabilidad Suarez", or a cron job invokes `/Users/manuelsuarez/bin/backup_contabilidad_diario.sh`.

## What the pipeline does (script: ~/bin/backup_contabilidad_diario.sh)
1. `python3 ~/bin/prender-server.py` — sends WOL magic packets to qbex (MACs `1c:86:0b:2d:e2:c8` and `44:87:fc:ea:69:da`).
2. Polls `ping 192.168.1.69` up to 100s; exits 1 with `FALLO: qbex no arranca` if no response.
3. `cd ~/.hermes/contabilidad && env -u PYTHONPATH ./venv/bin/python3 scripts/backup_qbex.py` — backs up LOCAL xlsx from the Mac (`contabilidad 2026.xlsx`, `contabilidad Renata suarez 2026.xlsx`, `contabilidad familia suarez 2026.xlsx`) + the `scripts/` folder, scp's them to qbex `/mnt/raid/backups/contabilidad_suarez/backup/`, then on qbex runs `git add -A && git commit -m "backup <tag>" && git tag -f v<tag>` where tag = `YYYY-MM-DD_HHMM`. **NOTE: the Google Drive token has been revoked since 2026-08 (invalid_client) — the backup NO LONGER pulls from Drive; it ships the local Mac xlsx. See `backup_qbex.py` docstring. Do not re-add Drive logic unless the token is regenerated (`_archive/backup_qbex_drive.py` has the old flow).**
4. SSH-confirms both xlsx exist on the RAID (`RESPALDO_CONFIRMADO` / `RESPALDO_FALTANTE`).
5. `ssh ... 'sudo systemctl poweroff -f'` — force power-off (bypasses logind/polkit that blocks a normal `shutdown` over non-active SSH).

## Automation via launchd (cierre_diario.py at 23:30)
`cierre_diario.py` (in `scripts/`) orchestrates the daily close: (1) `digest_diario.py` (summary from `logs/contabilidad.log.jsonl`), then (2) `backup_qbex.py` (Drive→qbex RAID + git tag). It is driven by `~/Library/LaunchAgents/com.suarez.contabilidad.cierre.plist` (a known-good copy is in `templates/cierre-diario.plist`).

**launchd + venv plist essentials (these bite you otherwise):**
- `EnvironmentVariables → PYTHONPATH` = `""` (empty string). The Hermes gateway exports a 3.11 PYTHONPATH that, injected before the contabilidad venv's own 3.9 site-packages, crashes `cryptography` with `symbol not found`. Emptying it makes the venv use its own packages. THIS IS MANDATORY for any venv Python run via launchd here.
- `WorkingDirectory` = `~/Library/LaunchAgents` parent of the project (so relative paths in the script resolve).
- `StandardOutPath` + `StandardErrorPath` MUST point to real files (create the `logs/` dir first). launchd discards stdout otherwise — there is no console.
- `StartCalendarInterval` Hour/Minute for the daily slot.
- `RunAtLoad` = false: `launchctl load` only REGISTERS the job; it does NOT run it. To run now, `launchctl start com.suarez.contabilidad.cierre`. Verify registration with `launchctl list | grep com.suarez.contabilidad.cierre` (the `0` in the middle column = last exit 0).

**Resilient offline backup (so launchd never reports a false failure):**
- qbex is headless and may be off (the S5 WOL gap in PITFALL 1). `backup_qbex.py` must NOT `sys.exit(1)` on hardware-off — that makes the whole cierre report `CIERRE_FAIL`. Instead: probe connectivity with a fast-timeout SSH; if offline, print `QBEX_OFFLINE` and `return` with rc=0.
- Fast SSH/SCP: `ssh -o ConnectTimeout=8 -o ServerAliveInterval=10 -o ServerAliveCountMax=2 -o BatchMode=yes`. Without these, a host-unreachable SSH hangs ~2 min per attempt (GNU `timeout` is absent on macOS — see `macos-bash-porting`, gotcha #3), stalling the launchd job.
- `cierre_diario.py` interprets `QBEX_OFFLINE` in backup output as `CIERRE_PARCIAL` (digest OK, backup skipped) with rc=0 — not `CIERRE_FAIL`.

## PITFALL 1 — qbex won't WOL-wake from full S5 power-off (MOST COMMON FAILURE)
- **Symptom:** `prender-server.py` reports `[OK] Magic packet enviado` for both MACs, but `ping 192.168.1.69` returns `Host is down` / 100% loss and the script dies at step 2 (`FALLO: qbex no arranca`, exit 1). No backup runs.
- **Cause:** qbex was shut down with `sudo shutdown -h now` (full S5). On this hardware WOL only fires from suspend/sleep — "Wake on LAN from S5" is NOT enabled in BIOS, so cold boots never wake.
- **Recovery (pick one):**
  - Press the physical power button on qbex (server01), wait ~30–60s, verify `ping 192.168.1.69` responds, then rerun `backup_contabilidad_diario.sh`.
  - OR enable BIOS "Wake on LAN" / "Power on by PCI-E" for S5 so future WOL works from cold.
- **Do NOT keep retrying WOL alone** — a cold S5 host here will never wake from magic packets. One or two retries max, then escalate to manual power-on.
- **But give the wake time to land before declaring it dead.** The magic packet only *starts* the boot; the box needs tens of seconds. Poll with a bounded loop instead of pinging once:
  `for i in 1 2 3 4 5 6; do sleep 15; ping -c1 -t2 192.168.1.69 >/dev/null 2>&1 && { echo "ARRANCO tras $((i*15))s"; break; }; echo "t=$((i*15))s off"; done`
  ~45s is a normal successful wake. Pinging once at 5–10s produces false "qbex apagado" reports.

## PITFALL 2 — "backup version / git tag" lives on qbex, NOT the Mac
- The version tag `vYYYY-MM-DD_HHMM` and the repo size are created on qbex's RAID repo `/mnt/raid/backups/contabilidad_suarez` (the script prints `SIZE:…`).
- The Mac-local repo `~/.hermes/contabilidad` holds only scripts + the Drive xlsx and has **no tags** (`git describe --tags` → `fatal: No names found`). So you cannot read "today's backup tag" or repo size from the Mac when qbex is off — report them as unavailable and explain why.
- When qbex is up, read latest tag with:
  `ssh -i ~/.ssh/id_ed25519_qbex user01@192.168.1.69 'cd /mnt/raid/backups/contabilidad_suarez && git tag --sort=-creatordate | head'`

## PITFALL 3 — shutdown is SLOW and its failure is SILENT (`|| true` hides it)
- The script ends with `ssh -i ~/.ssh/id_ed25519_qbex user01@192.168.1.69 'sudo systemctl poweroff -f' || true` (the `|| true` is deliberate — a failed poweroff must not fail the cron run).
- **It is SLOW.** `systemctl poweroff -f` drops sshd within seconds (a manual re-ssh right after shows `Connection refused`), but the box keeps answering **ping for ~30–60s** while it flushes disks and cuts power. If you ping immediately after the script's `FIN: qbex apagando` line you'll see STILL-ON — that's shutdown *in progress*, not a failure. **Wait ≥60s, then ping.** Only 100% loss = truly OFF. (Observed 2026-08-27: full OFF ~60s after FIN.)
- **It is SILENT.** `|| true` swallows any poweroff error. If qbex is STILL up after a ~90s wait, the poweroff likely genuinely failed — most often `sudo` prompting for a password in `BatchMode` SSH, or the key/key-perm broken. Diagnose by running it manually so you see stderr:
  `ssh -i ~/.ssh/id_ed25519_qbex user01@192.168.1.69 'sudo systemctl poweroff -f'`
  - `Connection refused` → shutdown already started, just wait and re-ping.
  - sudo/polkit "Access denied" or a password prompt → fix the `user01` NOPASSWD sudo rule for `systemctl poweroff` (or re-deploy the key), then re-run the script.

## Auditing qbex for script conflicts / structure ("revisa el server" requests)
When the user asks what scripts are in conflict on the server or what to unify:
1. **The server has NO scheduler for contabilidad.** `crontab -l` is empty for `user01` and there are no custom systemd timers — every job is driven from the Mac (launchd `com.suarez.contabilidad.cierre` + the two Hermes cron jobs). So there is never a scheduling conflict to find on the server side; don't hunt for one. Say so explicitly and keep the Mac as the single source of truth.
2. **`/mnt/raid/backups/contabilidad_suarez/` is a versioned SNAPSHOT, not a working copy.** It receives the Mac's `scripts/` via scp + git commit/tag. It is never executed there. Divergence therefore only ever means *stale backup*, not *conflicting live code*.
3. **Detect divergence with hashes, not dates.** Compute sha256 on both sides and diff programmatically:
   ```
   (cd ~/.hermes/contabilidad/scripts && shasum -a256 * )
   ssh -i ~/.ssh/id_ed25519_qbex user01@192.168.1.69 \
     'cd /mnt/raid/backups/contabilidad_suarez/backup/scripts && sha256sum *'
   ```
   A file present locally but absent remotely, or with a different hash, = the backup has been skipping. Cross-check the last successful run:
   `ssh ... 'cd /mnt/raid/backups/contabilidad_suarez && git log -1 --oneline && git tag --sort=-creatordate | head -3'`
   and the Mac side log: `tail -30 ~/.hermes/contabilidad/logs/cierre_diario.out.log` — `QBEX_OFFLINE: backup omitido` there explains a multi-day gap (qbex was off at 23:30 each night).
4. **Watch for duplicated-and-divergent utility scripts.** The same helper can exist in several places (`~/bin/`, `scripts/`, `/mnt/raid/proyectos_web/…`) with *different* hashes and byte counts. Report each path + hash + size and propose collapsing to ONE canonical executable location (the Mac `~/.hermes/contabilidad/scripts/`), never silently picking a winner.

### Protected Docker mounts on qbex — never move or rename these paths
Before proposing ANY RAID reorganization, run `docker inspect` on the service containers and treat every bind-mount source as frozen:
- `immich_server` mounts `/mnt/raid/immich` **and** `/mnt/raid/raid1_backup` (external library) — `raid1_backup` is a service root, not clutter.
- `nextcloud` mounts `/mnt/raid/nextcloud/data`.
- `code-server` mounts **all of `/mnt/raid`** as its project root, so every top-level change is visible inside the web IDE.
Present non-mounted directories (`site001`, staging `Descargas`, `hola.txt`, `LICENSE`, `tmp_etc_openclaw`, macOS `.DS_Store`/`._*`) as *candidates* and get confirmation per folder; moving a mounted path breaks a service.

### Remote-inspection plumbing (these two waste a whole call each)
- Never interpolate Go templates into `ssh host 'bash -lc "..."'` — `{{...}}` gets brace-expanded locally and the command dies. Pipe a heredoc instead, which also avoids nested-quote hell:
  `ssh -i ~/.ssh/id_ed25519_qbex user01@192.168.1.69 'bash -s' <<'EOS' … EOS`
- Scope `find` to explicit paths. A `find`/`du` sweeping all of `/mnt/raid` blows past a 120s timeout on this RAID; split into several small commands targeting named directories, and keep per-call timeouts generous.

## Verification
- Keep Hermes backups completely separate from Contabilidad and other computer-system data; use `/mnt/raid/backups/hermes/ver/` for Hermes versioned archives, never `/mnt/raid/backups/contabilidad_suarez/`.
- Before declaring a backup location correct, list the exact remote path and verify the archive exists, is non-empty, and its checksum matches the local source.
- Treat timestamped directories created by exploratory or intermediate copy commands as disposable staging areas: inspect their contents and remove them after the canonical archive is verified, because they can duplicate credentials and gigabytes of runtime data.
- qbex OFF: `ping -c5 -t3 192.168.1.69` → `Host is down` / 100% packet loss.
- qbex ON: ping responds; confirm backup via the script's `RESPALDO_CONFIRMADO` check.
- **Timing — wait ~60s before the OFF ping (see PITFALL 3):** the script prints `FIN: qbex apagando` the instant it *issues* `systemctl poweroff -f`; the box then keeps answering ping for ~30–60s while it flushes disks. Pinging right after FIN falsely reports STILL-ON. Also, a manual re-ssh during that window returns `Connection refused` (sshd already dropped) — that is shutdown *in progress*, not a failure. Only confirm OFF after ping goes 100% loss.

## Reporting a failed run
If qbex didn't wake: state BACKUP NOT RUN, give the WOL/S5 cause, confirm qbex OFF via ping, note tag+size unavailable (on qbex), and list the recovery action (manual power-on or BIOS WOL-from-S5, then rerun script). No data is lost at source — xlsx remain in Google Drive.

## Two separate Hermes cron jobs touch this backup — check BOTH when diagnosing a complaint
There are two independent scheduled jobs in `hermes cron list`, not one:
- **`Backup contabilidad diario 00:00`** (job id pattern varies per install,
  schedule `0 0 * * *`, `deliver: local`) — runs `backup_contabilidad_diario.sh`
  directly (the full WOL → backup → shutdown pipeline described above).
- **`Cierre diario contabilidad Suárez`** (schedule `30 23 * * *`, `deliver: all`
  — reaches Telegram/WhatsApp/etc.) — runs `cierre_diario.py`, which does its
  OWN digest + `backup_qbex.py` call, separate from the 00:00 job's script.

**A user complaint that arrives via Telegram/WhatsApp almost always traces to
the 23:30 `Cierre diario` job** (it's the one with `deliver: all`), even if
the complaint is phrased as "the backup didn't run." Check `hermes cron
runs <job_id>` / `hermes cron list` for BOTH job IDs before concluding which
one actually failed — don't assume the literally-named "Backup" job is the
culprit. Both jobs are unpinned-model-sensitive (see
`hermes-runtime-config`'s cron drift pitfall) and have failed together in the
past from the same `model.default` change, so a fix to one often needs to be
applied to the other too (`hermes cron edit <job_id> --provider ... --model ...`
for each).

## Verifying a run when Hermes's own cron status is stuck
Hermes' `hermes cron runs <job_id>` can show `status: running` indefinitely
even after the underlying script has fully finished (tracking artifact, not
a real hang — see `hermes-runtime-config`). Don't trust that field alone.
Confirm the ACTUAL outcome via the pipeline's own side effects instead:
```
ssh -i ~/.ssh/id_ed25519_qbex user01@192.168.1.69 \
  'cd /mnt/raid/backups/contabilidad_suarez && git log -1 --oneline'
ssh -i ~/.ssh/id_ed25519_qbex user01@192.168.1.69 \
  'ls -la /mnt/raid/backups/contabilidad_suarez/backup/'   # check today's mtime
ping -c1 -t3 192.168.1.69     # should go 100% loss once shutdown completes
```
A fresh git commit/tag timestamped today + files with today's mtime = the
backup genuinely succeeded, independent of what the cron status field says.

## Reference
`references/qbex-backup-detail.md` — exact commands and the 21 Aug 2026 WOL-failure transcript.
`templates/cierre-diario.plist` — known-good launchd plist (venv Python, PYTHONPATH cleared, logs to files). Copy to `~/Library/LaunchAgents/` and `launchctl load` it.
