---
name: whatsapp-setup
description: "Set up WhatsApp with Hermes: QR bridge or Meta Cloud."
version: 1.1.0
author: Hermes Agent (curated)
license: MIT
platforms: [macos, linux, windows]
metadata:
  hermes:
    tags: [hermes, whatsapp, messaging, qr, bridge, integration, setup]
---

# WhatsApp Setup on Hermes Agent

Use when the user wants to connect WhatsApp to the agent — "pair WhatsApp", "give me the QR for WhatsApp", "use WhatsApp with the bot", "configure WhatsApp", or when WhatsApp "se cayó" / "no responde" / "reconectando".

## Two adapters (pick the right one)

- **`hermes whatsapp`** — Baileys bridge, QR-code pairing, runs locally. No Meta business account needed. Best for personal / self-hosted use.
- **`hermes whatsapp-cloud`** — official Meta WhatsApp Business Cloud API. NO QR (uses Phone Number ID + Access Token + App Secret from Meta). Requires a verified WhatsApp Business account and webhook setup.

## CRITICAL GOTCHA — the QR is terminal-only

`hermes whatsapp` calls `_require_tty()` and prints the pairing QR as **ASCII art in the terminal where the command runs**. The chat agent CANNOT generate, capture, or relay that QR. Never promise to "send you the QR" in chat — tell the user to run the command themselves in a real terminal (Terminal.app, iTerm, or the Hermes desktop terminal pane — NOT the chat box). If the user expects the QR here, correct them early.

## Prerequisites

- `node` and `npm` on PATH (bridge script lives at `~/.hermes/hermes-agent/scripts/whatsapp-bridge/`).
- The wizard auto-runs `npm install` in the bridge dir if `node_modules` is missing (takes ~1–2 min, needs network). Verify with `node --version` / `npm --version` first.

## Getting a second number WITHOUT dual-SIM (iPhone users)

An iPhone can't hold two physical SIMs, but supports **eSIM**. To give Hermes its own WhatsApp number:
- Buy a **prepaid eSIM with a real phone number** (not data-only) and register a separate **WhatsApp Business** app on the iPhone with it.
- **Colombia:** Tigo and Movistar sell prepaid eSIMs with a real number online (~$4k–6.5k COP). Claro mostly requires postpaid for eSIM.
- **Google Voice / any VoIP number does NOT work** for WhatsApp verification — WhatsApp rejects VoIP. Do not suggest it as the 2nd number.
- **User style (Manuel):** keep all setup guidance terse and precise — bullet steps only, no verbose prose. He explicitly asked for "poco texto, sólo preciso y resumido" and repeatedly pushed back on long answers ("Mucho texto").
- **Avoid Airalo/Holafly data-only eSIMs** — WhatsApp verification rejects VoIP/data-only numbers. The eSIM must carry a real cellular number.
- After the eSIM + WhatsApp Business is live, run `hermes whatsapp` → mode `1` and scan the QR from that WhatsApp Business (Linked Devices).

## Setup flow (`hermes whatsapp`)

1. **Mode** → `1` = separate bot number (recommended; needs a 2nd WhatsApp number). `2` = self-chat (your own number; you message yourself).
2. **Allowed users** → your phone (`15551234567`) or `*` for anyone. Leaving it blank warns the agent will answer ALL incoming messages.
3. Bridge deps install automatically if absent.
4. **QR appears in the terminal** → on the phone: WhatsApp → Settings → Linked Devices → Link a Device, then scan. Scan promptly (the QR has a time window).
5. On success the wizard writes `WHATSAPP_ENABLED=true` and prints "✓ WhatsApp paired successfully!".
6. Start the gateway: `hermes gateway` (or `hermes gateway install` to run as a service).

## Inbound delivery — why the bot's OWN replies never arrive (bot mode)

This is the #1 silent failure after a successful QR pair. The bridge connects,
outbound `hermes send` works, but the user's text replies never reach the agent.

**Root cause (read the bridge code, don't guess):** in `WHATSAPP_MODE=bot`,
any message WhatsApp flags `fromMe: true` — i.e. sent FROM the bot's own
paired phone — is dropped by default. The dispatch loop calls
`classifyOwnerMessageGate({...})` and, when the owner-forward opt-in is OFF,
returns `drop_disabled` → `continue` (silently skipped). So:
- ✅ Outbound (`hermes send`, or agent replies) reach the user — those are
  sent BY the bridge, not received.
- ❌ Inbound replies typed on the bot's own phone are `fromMe` and discarded.

A second, subtler trap: even with the opt-in ON, the owner gate checks the
**chatId (the customer's JID) against `WHATSAPP_ALLOWED_USERS`**, NOT the
owner's number. When the owner talks to their own bot number, the chatId is
the bot's own number, which is usually NOT in the allowlist → `drop_allowlist`.
This is exactly why "personal use from the bot's phone" fights the bot-mode
design (which assumes a separate customer phone DMs the bot).

**Fixes, in order of preference:**
1. **Personal use (YOU chatting with the bot)? Use `WHATSAPP_MODE=self-chat`.**
   Then message the bot in WhatsApp → "Message Yourself" (Mensaje a ti mismo).
   The self-chat pinning logic accepts your own `fromMe` messages with no
   allowlist gymnastics. This is the clean path — switch mode and restart:
   set `WHATSAPP_MODE=self-chat` in `.env`, then
   `launchctl unload ~/Library/LaunchAgents/ai.hermes.gateway.plist && sleep 2
   && launchctl load ~/Library/LaunchAgents/ai.hermes.gateway.plist`.
2. **Must keep bot mode AND want owner replies?** Set in `.env`:
   `WHATSAPP_FORWARD_OWNER_MESSAGES=true`. Also add the bot's own number to
   `WHATSAPP_ALLOWED_USERS` (comma-separated) so the owner→bot chatId passes
   the allowlist gate, then restart the gateway. Expect the `drop_allowlist`
   caveat above — if replies still don't land, self-chat mode is the real fix.

**Diagnostic recipe (don't eyeball it):**
- Enable `WHATSAPP_DEBUG=true` in `.env` and restart → the bridge logs every
  `ignored` event (`reason: drop_disabled` / `drop_allowlist` /
  `allowlist_mismatch_owner_chat`) plus an `upsert` debug event per message.
- In `~/.hermes/logs/gateway.log`, grep for `inbound message: platform=whatsapp`.
  **Zero whatsapp inbound lines = messages are dropped at the bridge, not the
  gateway.** Telegram shows as `platform=telegram`; if only telegram appears,
  suspect the fromMe drop above.
- Confirm bridge is alive: `pgrep -fl whatsapp-bridge/bridge.js` and a
  `✓ whatsapp connected` line in gateway.log.

## Bridge lifecycle — restart, reconnection, and session loss

The WhatsApp bridge runs as a separate Node.js process (`bridge.js`) on port 3000.
The gateway connects to it. The bridge handles the actual WhatsApp connection.

### How the bridge process is managed

- **Normal run**: the bridge is started by the gateway's WhatsApp integration when `WHATSAPP_ENABLED=true`. It listens on port 3000 and maintains the Baileys session in `--sessionDir` (default `~/.hermes/`).
- **Session files**: Baileys stores credentials in `creds.json` inside the session directory (e.g. `~/.hermes/whatsapp/session/creds.json`). This file holds the authentication state — **do NOT delete it unless you intend to re-pair**.
- **Gateway restart does NOT restart the bridge** if the bridge process is already dead. If the bridge crashes, the gateway will log reconnect attempts but the bridge won't come back on its own.

### Diagnosing a dead bridge

```bash
# Is the bridge process running?
pgrep -fl "node.*bridge.js"

# Is port 3000 listening?
lsof -i :3000

# Gateway log: is it trying to reconnect?
tail -50 ~/.hermes/logs/gateway.log | grep -i whatsapp

# Bridge log: what happened?
tail -50 ~/.hermes/whatsapp/bridge.log
```

### Reconnecting after a crash

1. **Check if the bridge process died**: `pgrep -fl "node.*bridge.js"` → empty = process dead.
2. **Restart the bridge manually** (background):
   ```bash
   cd ~/.hermes/hermes-agent/scripts/whatsapp-bridge
   nohup node bridge.js --port 3000 --sessionDir ~/.hermes/ \
     > ~/.hermes/whatsapp/bridge.log 2>&1 &
   ```
   Wait ~5s, then check: `lsof -i :3000` and `tail ~/.hermes/whatsapp/bridge.log`.
3. **If the bridge starts and connects** (`✅ WhatsApp conectado!` in log), the session survived — good.
4. **If the bridge connects but immediately disconnects** with `❌ Cierre de sesión. Elimina la sesión y reinicia para volver a autenticar.` → the Baileys session is invalid. WhatsApp remotely logged out the bridge or invalidated the session. **Fix: delete the session and re-pair.**

### Session invalidation — when to delete and re-pair

Delete the session only when the bridge shows session-invalidated errors:
```bash
# Delete the session (re-pair required after)
rm -rf ~/.hermes/whatsapp/session
# Then restart bridge — it will generate a new QR
```

**Do NOT delete the session on every reconnect failure** — most failures are bridge process crashes where the session is still valid. Deleting unnecessarily forces a re-pair.

### What "colgado" means for the auth URL (Google OAuth — different domain)

Not WhatsApp, but similar pattern: when the Google auth URL "hangs" after approval, the code is in the redirect URL bar (`http://localhost:1?code=...`). Copy the full URL and paste it. There is no page to load. If it truly hangs with no code, it's Testing mode — add the user as a test user in Google Cloud Console.

## Pitfalls

- If pairing is aborted (Ctrl+C, missed scan), `WHATSAPP_ENABLED` stays UNSET so `hermes gateway` skips WhatsApp cleanly — re-run `hermes whatsapp` to retry.
- Re-pairing clears the existing `creds.json` session.
- Self-chat replies are prefixed `⚕ Hermes Agent` so you can tell them apart from your own messages.
- The bridge uses Baileys (whatsapp-web style) — pairing is a WhatsApp-Web-style linked device, so it follows the same "Linked Devices" UX on the phone.
- **Bot-mode inbound drop (silent):** replies typed on the bot's own phone are `fromMe` and discarded unless `WHATSAPP_FORWARD_OWNER_MESSAGES=true`. For personal use, prefer `WHATSAPP_MODE=self-chat`. See "Inbound delivery" above.
- Empty `WHATSAPP_ALLOWED_USERS` = NO ONE allowed (secure default; `*` = open). A blank allowlist in bot mode silently drops ALL customer DMs.
- **`stream errored out (code 515)` during pairing is harmless.** A `stream errored out` + `transaction failed, rolling back` followed by `↻ WhatsApp requested restart (code 515). Reconnecting…` and a subsequent `✅ WhatsApp connected!` is normal Baileys handshake behavior — do NOT abort the pairing, do NOT tell the user to retry from scratch. Confirm the run succeeded only on `✓ WhatsApp paired successfully!` in the wizard output. After pairing, start the gateway (`hermes gateway` / `launchctl kickstart -k gui/$(id -u)/ai.hermes.gateway`) before testing messages.
- **`No session found to decrypt message` for `status@broadcast` after pairing is harmless.** The Baileys status-broadcast listener can fire before the group-cipher session is fully established; the error is logged at level 50 and ignored. Self-chat mode is unaffected. No action needed.
- **Bridge process dead = gateway reconnect loop.** When the bridge process dies (crash, kill, exit), the gateway logs reconnect attempts every ~5 minutes but cannot reconnect because there's no bridge to connect to. The fix is to restart the bridge process (`nohup node bridge.js ... &`), not to re-pair. Re-pair is only needed when the session itself is invalidated (logout/error en el log del bridge).
- **macOS: `timeout` command does NOT exist** — use `nohup ... &` + manual sleep + `lsof` to background the bridge. On Linux, `timeout 60 node bridge.js` works.
- **node bridge.js vs node bridge.mjs**: the bridge script is `bridge.js` (or `bridge.mjs` depending on version). Check the actual file name in the scripts directory before running. `ls ~/.hermes/hermes-agent/scripts/whatsapp-bridge/`.
