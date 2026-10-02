---
name: homelab-wake-on-lan
description: "Power on/off homelab servers (qbex/server01, etc.) via Wake-on-LAN magic packets and SSH. Verify server state, send WOL to multiple MACs, and manage power lifecycle."
version: 1.1.0
author: Hermes Agent (curated)
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [homelab, wake-on-lan, wol, server, power, qbex, server01, ssh]
---

# Homelab Wake-on-LAN and Power Control

Use when the user wants to power on/off a homelab server — "prende el server", "apaga el server", "wake on lan", "WOL", "server01", "qbex", "192.168.1.69" — or when a backup/power script needs to be verified or run.

## Server inventory (Manuel's homelab)

| Server | IP | User | Auth | Notes |
|---|---|---|---|---|
| qbex / server01 | 192.168.1.69 | user01 | SSH key `~/.ssh/id_ed25519_qbex` + password fallback (onetwotres) | Debian; WOL MACs: `1c:86:0b:2d:e2:c8`, `44:87:fc:ea:69:da` |
| Mac Mini (gateway) | 192.168.1.5 | — | — | Runs Hermes; Tailscale 100.101.1.51 |
| ThinkPad | 192.168.1.117 | — | — | Separate machine |

## WOL: the reliable pattern

WOL magic packets are UDP broadcast to port 9 (or 7). The packet must reach the server's NIC *before* the server powers on (i.e. while it's off, the NIC listens in low-power mode).

**Two-MAC redundancy**: qbex has two NIC MACs. Send to BOTH. The script `prender-server.py` does this.

### Quick check: is WOL working?

```bash
# Send WOL
python3 /Users/manuelsuarez/bin/prender-server.py

# Wait 30-60s, then check
ping -c 5 -t 5 192.168.1.69
```

If ping returns 100% loss after 60s → WOL did not wake the server. Possible causes:
- **WOL disabled in BIOS** of the server (cannot be fixed remotely)
- **NIC WOL inactive** — some NICs disable WOL after AC power loss or require a specific PCIe slot
- **Network blocking** — broadcast UDP port 9 blocked by switch/AP
- **Wrong MAC** — verify the MAC addresses in the script match `arp -a` or the server's NIC when it's on

### WOL script: `prender-server.py`

Location: `/Users/manuelsuarez/bin/prender-server.py`

What it does:
1. Sends magic packet to **both** MACs of qbex: `1c:86:0b:2d:e2:c8` and `44:87:fc:ea:69:da`
2. Broadcasts via `192.168.1.255:9` (the LAN broadcast address)
3. Prints `[OK]` for each packet sent
4. Tells you to verify with `python3 prender-server.py --check` (ping)

Usage:
```bash
python3 /Users/manuelsuarez/bin/prender-server.py       # send WOL
python3 /Users/manuelsuarez/bin/prender-server.py --check  # verify (ping)
```

### Why WOL to 192.168.1.255:9 works (and when it doesn't)

The broadcast address `192.168.1.255` reaches all hosts on the `192.168.1.0/24` subnet. Port 9 is the standard WOL discard port. This works when:
- The server and the sender are on the **same L2 subnet** (no router in between)
- The server's NIC has WOL enabled in BIOS and the OS driver

It fails when:
- The server is on a **different VLAN or subnet** — need directed WOL or a WOL proxy
- A managed switch blocks broadcast UDP
- The server's BIOS has "Wake on PCI-E" or "Wake on LAN" **disabled**

## SSH access to qbex

**Key-based**: `~/.ssh/id_ed25519_qbex` (exists).

```bash
ssh -i ~/.ssh/id_ed25519_qbex -o StrictHostKeyChecking=no -o ConnectTimeout=10 user01@192.168.1.69 'uptime'
```

Password fallback (when key is not available): user `user01`, password `onetwotres`. **Never persist this password in files** — use `expect` for one-shot scripts or pass via stdin with `-o PreferredAuthentications=password`.

**Note**: `sudo` on the Mac Mini (gateway) does NOT accept stdin (sandbox/framework blocks it). This does NOT affect qbex SSH — qbex accepts key-based SSH normally. The sudo limitation is only for the Mac Mini itself (e.g. `systemsetup -setremotelogin on`).

## Power cycle: full backup script

`/Users/manuelsuarez/bin/backup_contabilidad_diario.sh` — a complete cycle:
1. Send WOL to qbex
2. Wait for ping response
3. Mount/access Drive (requires valid Google OAuth token)
4. Run backup to qbex via SSH (using `id_ed25519_qbex` key + `systemctl poweroff -f`)
5. Confirm backup
6. Power off qbex

This script requires:
- Google Drive token valid (not revoked)
- SSH key `id_ed25519_qbex` present
- qbex reachable after WOL

## When WOL fails (troubleshooting)

1. **Verify server is actually off**: `ping -c 3 192.168.1.69` → 100% loss confirms off.
2. **Send WOL**: `python3 prender-server.py`
3. **Wait 60s, ping again**: `ping -c 5 192.168.1.69`
4. **If still off**: 
   - Check MACs are correct: compare `prender-server.py` MACs with what `arp -a` showed when server was last on
   - Try sending WOL directly to each MAC's IP (if the NIC has an IP assignment that persists in WOL mode)
   - Consider: BIOS WOL may be disabled — physical access needed
   - Consider: server may need a power cycle (pull power, wait, reconnect) to re-enable WOL

## Pitfalls

- **WOL does not work across routers/VLANs** — it's L2. If qbex moves to a different subnet, WOL from the Mac Mini won't reach it.
- **Two MACs on qbex**: send to both. One may be the onboard NIC (active in WOL), the other a PCIe NIC (may not support WOL).
- **Password persistence**: never write `onetwotres` or any server password to disk. Use `expect` for one-shot SSH-with-password, and delete the expect script immediately after.
- **sudo on Mac Mini is unusable via stdin** — for remote SSH/Screen Sharing on the Mac Mini, the user must manually enable it in System Settings → Sharing. Do not attempt `sudo systemsetup` from scripts.
- **backup_contabilidad_diario.sh requires Drive token** — if Google token is revoked, the backup step fails. Refresh token before running the script.
- **After WOL, wait 30-60s** — Debian boot takes time. Don't poll too fast.

## Files

- `/Users/manuelsuarez/bin/prender-server.py` — WOL sender (two MACs, broadcast)
- `/Users/manuelsuarez/bin/backup_contabilidad_diario.sh` — full backup cycle (WOL + Drive + SSH + shutdown)
- `~/.ssh/id_ed25519_qbex` — SSH key for qbex
- `/tmp/qbex_off.exp` — temporary expect script for password-based shutdown (created on demand, deleted after)

## Related

- `google-workspace` — for Drive token validity (required by backup script)
- `whatsapp-setup` — for WhatsApp bridge (unrelated domain)
