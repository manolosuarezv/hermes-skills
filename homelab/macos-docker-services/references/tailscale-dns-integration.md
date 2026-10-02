# Tailscale + self-hosted DNS (Pi-hole) integration

Pattern: expose a DNS/adblock service running on the Mac Mini to all Tailscale
clients, including devices off the home LAN (ThinkPad, phone on cellular).

## Prereqs
- Tailscale already running on the Mac Mini (check: `pgrep -fl io.tailscale`
  or the `utun4` interface with a `100.x` IP in `ifconfig`).
- The service binds to all interfaces / accepts non-local queries. For Pi-hole
  v6 set `FTLCONF_dns_listeningMode: 'all'` in the compose env, otherwise it
  refuses Tailscale-origin (100.x) queries.

## Steps in the Tailscale admin console (login.tailscale.com)
1. DNS → Nameservers → Add nameserver → Custom.
2. Enter the Mac Mini's Tailscale IP, e.g. `100.101.1.51`.
   (Better: use MagicDNS hostname `macmini.<tailnet>.ts.net` so it survives
   IP changes — but the custom-nameserver field wants an IP; the robust play
   is: add the IP now, and note in docs to update if it changes. Some setups
   allow the MagicDNS name in newer Tailscale versions.)
3. Toggle "Use Tailscale DNS settings" / "Override local DNS" ON — this makes
   connected devices send all DNS through Tailscale (i.e. through Pi-hole).
4. Optionally enable "HTTPS certificates" if you later want the admin UI on a
   TLS name; not required for DNS-only.

## Verify from a Tailscale client (or the Mac itself)
  dig @100.101.1.51 wikipedia.org     # -> IP means Pi-hole answered over TS
  dig @100.101.1.51 doubleclick.net   # -> 0.0.0.0 / NXDOMAIN = blocked

## Notes
- Tailscale's CGNAT range is 100.64.0.0/10. Pi-hole's "all origins" covers it.
- Do NOT add the LAN IP (192.168.1.5) as the Tailscale nameserver — remote
  clients can't route to RFC1918 via Tailscale magic by default; use the 100.x.
- If clients still use local DNS, confirm "Override local DNS" is on AND the
  device's Tailscale client allows it (some OSes need "Use Tailscale DNS" in
  the client's settings).
