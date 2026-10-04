---
name: homelab-server-control
description: "Power off/on headless homelab servers via expect ssh."
version: 1.0.0
author: Hermes Agent (session-derived)
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [homelab, ssh, expect, server, power, debian, tailscale, shutdown]
---

# Homelab Server Control

Use when the user asks to power on/off, check status of, or run a privileged command on a headless server in their homelab (e.g. "apaga el server01", "prende el qbex", "revisa si la máquina X está arriba", "apaga la ip 69").

## Topology (user: <TU_NOMBRE> — homelab, LAN 192.168.1.0/24)
- **server01** = 192.168.1.69, Debian 13 (trixie), SSH user `user01`. The user sometimes calls it **"qbex"**.
- **ThinkPad** = 192.168.1.117 (Linux, CachyOS/Hyprland).
- **Mac Mini** = headless macOS, reachable via Tailscale `100.101.1.51` (HOSTNAME_MAC). This runs the Hermes gateway — see Pitfalls.
- Credentials are shared across these boxes (same password as the Mac sudo). Do NOT persist plaintext creds in memory or files — pass inline and clean up immediately.

## STEP 0 — Pre-shutdown dependency check (ALWAYS do this first)
Before powering anything off, confirm nothing depends on the target:
- `lsof -i | grep <IP>` — active connections from this host to the target
- `mount | grep <IP>` — mounted filesystems from the target
- `grep -ri <IP> ~/.ssh/config /etc/hosts` — static references
- `crontab -l | grep <IP>` and `hermes cron list | grep <IP>` — scheduled jobs
- `grep -ri <IP> ~/.hermes/config.yaml` — Hermes wiring
If ANY dependency is found, stop and tell the user before shutting down.

## STEP 1 — SSH with password (no key, no sshpass)
macOS ships `expect` at `/usr/bin/expect` but NOT `sshpass` and NOT `pexpect` (python3). Use an expect script.

1. Write a temporary expect script from `templates/shutdown.exp` (fill IP, user, pass).
2. Run: `expect /tmp/qbex_off.exp` (or your temp path).
3. **Immediately `rm -f` the script** so the password never lingers on disk.

Do NOT:
- Put the password in `~/.hermes/.env` as `SUDO_PASSWORD` — the framework reads it but it does NOT bypass the interactive sudo approval gate; useless here and the path is protected from writes anyway.
- Use `setsid ... &` shell wrappers in the terminal tool — the framework blocks them ("shell-level background wrappers"). Use `terminal(background=true)` if you must background.

## STEP 2 — Verify power state
- **ON**: `ping -c 2 -t 3 <IP>` → 0% packet loss.
- **OFF**: `ping -c 3 -t 3 <IP>` → 100% loss. Wait and re-verify — do NOT trust a single immediate post-command ping.
- **Forced `poweroff -f` on a RAID box can take MINUTES, not seconds.** During the unmount window the NIC may still answer ICMP (ping 0% loss) while port 22 is already filtered — so "ping works but SSH times out" does NOT mean the host is up-and-banned. Re-ping on a loop; the transition to **100% loss** is the real OFF signal. Confirmed 2026-08-19: qbex answered ping for ~3 min after `systemctl poweroff -f`, then flipped to 100% loss = truly off. See `references/sshguard-shutdown-diag.md`.

## Pitfalls
- `sudo -S systemctl poweroff -f` (preferred, confirmed on Debian 13 agosto 2026) or `shutdown -h now` over SSH often returns "Connection reset by peer" / "Broken pipe" — that is SUCCESS (the host killed its network as it went down), not an error. Confirm with a follow-up ping showing 100% loss.
- SSH may report `Permission denied (publickey,password)` with `BatchMode=yes` — that just means key auth failed and it wants a password; expect handles it.
- **Never `launchctl unload` the Hermes gateway from inside the gateway process** — the framework blocks it ("cannot restart or stop the gateway from inside the gateway process") and warns. If the user asks to stop the gateway while you are actively chatting through it, refuse and explain you are using it right now.
- Do not confuse a homelab server with the Mac Mini gateway.
- **sshguard / port-22 DROP after failed or rapid SSH.** If you can `ping` the host (ICMP 0% loss) but `ssh`/`nc -z <IP> 22` hang or report `Operation timed out` (NOT `Connection refused`), the source IP is likely **banned by sshguard** on the target — triggered by the script's `BatchMode`/failed SSH attempts. Signature: ping OK + port 22 silently DROP (no RST). It auto-expires (often >2 min, sometimes much longer). Distinguish from a shutdown-in-progress: a **ban PERSISTS** (ping stays 0%, port stays filtered, never progresses to off), whereas a forced shutdown eventually reaches 100% loss. To bypass a ban mid-task, pivot the SSH *source* to another LAN host (e.g. ThinkPad 192.168.1.117) whose IP is not banned — only if that host is itself reachable. See `references/sshguard-shutdown-diag.md`.
- **Silent shutdown failure with `BatchMode` + `|| true`.** A `sudo … poweroff` invoked over SSH with `BatchMode=yes` has no tty, so `sudo` prompts for a password and the command fails — but `|| true` (or `2>&1 | tail`) swallows the error and the host stays ON while the script reports success. Always drive privileged shutdown through `expect` (STEP 1), never through a bare `BatchMode` sudo. This is exactly why `backup_contabilidad_diario.sh`'s inline `sudo systemctl poweroff -f || true` is fragile.

## Safe RAID organization and service-aware file moves
When organizing files on a homelab RAID, audit before changing anything:
1. List first-level directories and inspect candidate contents and sizes; classify service data, backups, projects, and personal documents.
2. Before moving a directory, inspect active Docker mounts with `docker inspect <container> --format '{{range .Mounts}}{{.Source}} -> {{.Destination}} ({{.Type}}){{println}}{{end}}'` and check container health with `docker ps`.
3. Treat directories mounted into active services as protected. Do not move or rename service roots or their internal subdirectories manually; this can break bind mounts, databases, generated thumbnails, or media indexes. For Immich, protect its data root, library, thumbnails, encoded video, uploads, backups, and any externally mounted source paths. For Nextcloud, manage user files through Nextcloud or its maintenance commands rather than moving its data directory manually.
4. For a proposed merge, inventory both trees, compute relative-path overlap, and perform a dry run before changing state. Move only when there are no path conflicts; verify the destination contents and that the source directory is gone afterward.
5. Keep technical service data (`immich`, `nextcloud`, code-server, databases) separate from human documents. Use a clear canonical name such as `Documentos`, and remove an empty legacy directory only after verification.
6. When the request is ambiguous about the target category, report candidates and ask before moving; do not infer that a backup, service directory, or historical archive is disposable.

## User style
Manuel wants terse, precise, bullet-only answers ("poco texto, sólo preciso y resumido"). Keep responses short — bullets, no verbose prose.
