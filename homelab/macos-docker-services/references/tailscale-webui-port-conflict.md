# Web UI works on LAN but NOT over Tailscale (port conflict + MagicDNS gotcha)

Real failure seen: Pi-hole container healthy, DNS answering on LAN (192.168.1.5)
AND Tailscale (100.101.1.51), web UI reachable on `192.168.1.5:8080` (HTTP 302)
but `http://100.101.1.51:8080/admin/` returned HTTP 000 (timeout). Root cause:
another process (the Hermes agent's own Python listener) had already bound port
8080 — but ONLY on the Tailscale interface — so the port was "free" on LAN yet
occupied on TS. OrbStack still bound 8080->80 for the LAN side; TS side collided.

## Debugging recipe
1. Container healthy? `docker ps` -> STATUS "healthy".
2. DNS on all three interfaces:
   `dig +short @127.0.0.1 google.com`        # loopback
   `dig +short @192.168.1.5 google.com`      # LAN  (use the Mac's LAN IP)
   `dig +short @100.101.1.51 google.com`     # Tailscale (use the Mac's TS IP)
   All returning IPs => DNS service is fine everywhere.
3. Web UI on all three:
   `curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:PORT/admin/`
   `curl -s -o /dev/null -w "%{http_code}\n" http://192.168.1.5:PORT/admin/`
   `curl -s -o /dev/null -w "%{http_code}\n" http://100.101.1.51:PORT/admin/`
   - 302 = alive (redirect to login). 000 = cannot connect.
4. If loopback/LAN = 302 but Tailscale = 000 (and DNS-over-TS worked in step 2),
   the host port is occupied on the Tailscale interface. Find the culprit:
   `sudo lsof -iTCP:PORT -sTCP:LISTEN`
   Output seen:
     Python   25289 manuelsuarez ... TCP HOSTNAME_MAC.tailcda3ff.ts.net:http-alt (LISTEN)
     OrbStack 27336 manuelsuarez ... TCP *:http-alt (LISTEN)
   The Python line binds only the Tailscale FQDN, stealing that port there.
5. Fix: change the host port in docker-compose.yml (8080 -> 8088),
   `docker compose up -d` to recreate, re-run the curl checks. 8088 worked.

## MagicDNS FQDN discovery (so you hand the RIGHT name)
- `tailscale status` -> self line, 1st column = machine name, e.g. `HOSTNAME_MAC`.
  This is NOT the macOS Computer Name (`HOSTNAME_MAC`).
- Tailnet domain = the part between machine name and `.ts.net` in any FQDN.
  Find it via `sudo lsof -iTCP:<port> -sTCP:LISTEN` (prints `<fqdn>:<port>`),
  or from a MagicDNS lookup. Here it was `tailcda3ff` -> FQDN
  `HOSTNAME_MAC.tailcda3ff.ts.net`.
- Validate: `dscacheutil -q host -a name HOSTNAME_MAC.tailcda3ff.ts.net`
  -> should resolve to the 100.x IP.
- Guessing a "nice" name like `macmini.<tailnet>.ts.net` FAILS with
  "DNS address could not be found" — there is no such record.

## Why no negative claim about Tailscale
The tunnel was fine the whole time; only the host port collided on one interface.
Do NOT conclude "Tailscale DNS is broken" — verify each layer (DNS query vs web
socket vs port binding) separately before blaming the VPN.
