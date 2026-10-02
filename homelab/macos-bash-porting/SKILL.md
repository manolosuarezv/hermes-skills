---
name: macos-bash-porting
description: Port Linux bash scripts to the macOS Mac mini gateway.
---

# Porting Linux bash scripts to macOS (homelab gateway)

The Mac mini is the homelab gateway / Hermes host, but most scripts are authored on
ThinkPad Debian. macOS is BSD-derived: many GNU/Linux assumptions break *silently*
(wrong branch taken, check always fails). This skill captures the gotchas that bit
us porting `prender-server` v5.1 (Wake-on-LAN orchestrator for qbex/server01).

## When to use
- User asks to "install this version on the Mac mini" / "adapt this script to macOS".
- A bash script works on Debian/ThinkPad but takes the wrong branch or fails quietly on macOS.

## Pre-flight recon (macOS)
```bash
uname -s            # -> Darwin
sw_vers             # macOS version
command -v brew wakeonlan mosquitto_pub tailscale ssh nc  # which deps exist
route -n get 8.8.8.8
ifconfig | awk '/inet / && $2 != "127.0.0.1"{print $2}'
```
Install homelab deps without sudo: `brew install wakeonlan mosquitto`.
`tailscale` is often ABSENT on the Mac — detect and skip DNS steps gracefully.

## macOS gotchas (the real fixes)

1. **IP / location detection.** Linux `ip route get 8.8.8.8` prints `src 192.168.1.x`.
   macOS `route -n get 8.8.8.8` does NOT print `source:` — it prints `interface: en0`.
   Get the IP with `ipconfig getifaddr en0`. Fallback: first non-loopback `ifconfig` inet line.

2. **Don't contaminate `$(func)` captures.** If a function both logs to stdout AND
   `echo`es its return value, `LOCATION=$(detect_location)` captures the log text too →
   `[2026-..] IP..home` fails `if [ "$LOCATION" = "home" ]` and the script silently
   falls into the remote branch. Fix: send logs to **stderr** (`log INFO "..." >&2`).

3. **No GNU `timeout` on macOS.** `check_ssh() { timeout 3 nc -z ...; }` always fails
   (`timeout: command not found` → check returns non-zero even when port is open).
   Use `nc`'s native timeout: `nc -z -w 3 -G 3 host port` (`-w` total, `-G` connect).
   Alt: `brew install coreutils` for `gtimeout`.
   **In Python scripts** (the contabilidad pipeline is Python, not bash): do NOT shell
   out to GNU `timeout` — it is absent and the call dies with
   `/bin/bash: timeout: command not found`. Pass `timeout=N` directly to
   `subprocess.run([...], timeout=N)` instead. (This is what `backup_qbex.py` and the
   verification harness use; a `timeout` wrapper hung 60s+ on an unreachable host.)

4. **TLS cert path differs.** Linux MQTT/TLS uses `--capath /etc/ssl/certs/`. On macOS
   that dir is absent; brew openssl keeps certs at `/opt/homebrew/etc/openssl@3/certs`.
   Detect and fall back instead of hardcoding the Linux path.

5. **`ping` flags differ.** macOS `ping -c 1 -t 2` (timeout in seconds via `-t`);
   Linux uses `-W`. Both accept `-c`.

6. **`nc` is BSD** — `nc -z` works for port checks; apply `-w/-G` as in #3.

## Verification pattern (avoid hanging the test)
- Break large `write_file`/`terminal` calls into <8K-token chunks (stream timeouts otherwise).
- Test WOL against a REAL OFF target; measure wake time (~50s for qbex).
- Test SSH with `-o BatchMode=yes -o StrictHostKeyChecking=accept-new -i <keyfile>`.
- Run the script with shortened `MAX_CYCLES`/`GLOBAL_TIMEOUT`/`PING_WAIT` via a
  sed-derived copy; replace the final `ssh` with `echo` so the test doesn't open an
  interactive session that hangs. THEN do one REAL ssh pass to confirm end-to-end.
- Force a location branch by stubbing `detect_location` or hardcoding the captured var.

See references/prender-server-macos.md for the concrete worked example (the three
bugs above, with before/after snippets, and the test matrix that proved it works).
