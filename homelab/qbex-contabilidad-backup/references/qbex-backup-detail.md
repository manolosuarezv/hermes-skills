# qbex Contabilidad Backup — detail & transcript

## Key commands
- Run backup: `/Users/manuelsuarez/bin/backup_contabilidad_diario.sh`
- WOL only: `python3 /Users/manuelsuarez/bin/prender-server.py` (sends magic packets to both MACs)
- Ping check: `ping -c5 -t3 192.168.1.69`
- Read latest backup tag (qbex up):
  `ssh -i ~/.ssh/id_ed25519_qbex user01@192.168.1.69 'cd /mnt/raid/backups/contabilidad_suarez && git tag --sort=-creatordate | head'`
- Force power-off (over SSH): `ssh -i ~/.ssh/id_ed25519_qbex user01@192.168.1.69 'sudo systemctl poweroff -f'`

## 21 Aug 2026 — WOL failure transcript (real)
Script log (`/tmp/backup_contabilidad_YYYYMMDD.log`):
```
=== Fri Aug 21 00:00:30 -05 2026 INICIO backup diario contabilidad ===
Enviando WOL a qbex (interfaces: 1c:86:0b:2d:e2:c8, 44:87:fc:ea:69:da)...
[OK] Magic packet enviado a 1c:86:0b:2d:e2:c8 via 192.168.1.255:9
[OK] Magic packet enviado a 44:87:fc:ea:69:da via 192.168.1.255:9
Espera ~30-60s y verifica con: python3 prender-server.py --check
FALLO: qbex no arranca
```
Manual re-WOL attempt + 45s wait: ping still 100% loss / `Request timeout`.
Final ping: `Host is down`, 0/3 received.

## Why it failed
qbex had been fully shut down on 16 Aug 2026 via `sudo shutdown -h now` (S5).
WOL from S5 is not enabled in BIOS on this Debian box, so magic packets are
ignored when the host is cold. WOL does work from suspend/sleep.

## Recovery (in order)
1. Retry WOL 1–2x (cheap) — only helps if qbex was merely suspended.
2. If still down: physically press qbex power button, wait 30–60s, verify ping,
   then rerun `backup_contabilidad_diario.sh`.
3. To make WOL work from cold going forward: enable BIOS "Wake on LAN" /
   "Power on by PCI-E" for S5 state.

## Notes
- Tag format on qbex RAID repo: `vYYYY-MM-DD_HHMM` (force-created each run).
- Mac-local `~/.hermes/contabilidad` has NO tags — do not query it for version.
- Data-at-rest safety: xlsx stay in Google Drive; a missed RAID copy is not data loss.
