# prender-server v5.1 → macOS port (worked example)

## Context
`prender-server` is a bash WOL orchestrator that wakes qbex (server01, user01@192.168.1.69,
Tailscale 100.119.118.124). Original authored for ThinkPad/Debian. Ported to the Mac mini
(macOS 26.5.2) as `~/bin/prender-server`. Detects home vs remote; home = WOL broadcast LAN,
remote = WOL via MQTT→ESP32 + `tailscale set --accept-dns=false`.

Constants: HOST_LOCAL=192.168.1.69, HOME_SUBNET=192.168.1, MAC1=44:87:fc:ea:69:da,
MAC2=1c:86:0b:2d:e2:c8, BROADCAST_LOCAL=192.168.1.255.

## The 3 bugs found & fixed (before → after)

### Bug 1 — location detection (macOS has no `source:` in `route`)
BEFORE (Linux-only):
```bash
src_ip=$(route -n get 8.8.8.8 2>/dev/null | awk '/source/{print $2}')
```
AFTER:
```bash
iface=$(route -n get 8.8.8.8 2>/dev/null | awk '/interface:/{print $2}')
src_ip=$(ipconfig getifaddr "$iface" 2>/dev/null)
[ -z "$src_ip" ] && src_ip=$(ifconfig | awk '/inet / && $2!="127.0.0.1"{print $2; exit}')
```

### Bug 2 — `$(detect_location)` captured log noise → wrong branch
BEFORE: `log INFO "IP de salida..."` went to stdout, so `LOCATION` = `[ts] IP..home`.
AFTER: `log INFO "..." >&2` (stderr). Now `LOCATION` cleanly = `home`/`remote`.

### Bug 3 — `timeout` missing on macOS (check_ssh always failed)
BEFORE: `timeout 3 nc -z -w 2 "$1" "$SSH_PORT"`
AFTER: `nc -z -w 3 -G 3 "$1" "$SSH_PORT"`  (BSD nc native timeout; `-G` connect timeout)

Plus: MQTT `--capath /etc/ssl/certs/` → detect `/opt/homebrew/etc/openssl@3/certs`;
`tailscale` absence detected and DNS step skipped.

## Test matrix (real, on Mac mini)
| Check | Result |
|---|---|
| `wakeonlan -i 192.168.1.255 <MAC>` to OFF qbex | ON in ~50s ✓ |
| `ssh -i id_ed25519_qbex user01@192.168.1.69` | CONECTADO_REAL / server01 ✓ |
| Script end-to-end (home, qbex ON) | WOL→ping→port22→SSH real, exit 0 ✓ |
| MQTT remote branch | NOT verified from home (would need off-network); left wired with brew certs |

## Notes
- qbex left OFF at end (shutdown via `sudo shutdown -h now` over ssh).
- Local minimal Python WOL skill (`prender-server.py`) is a subset; this bash v5.1 is the full version.
