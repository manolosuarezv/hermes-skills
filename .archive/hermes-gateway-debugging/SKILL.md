---
name: hermes-gateway-debugging
description: "Debug Hermes gateway hangs, esp. Telegram 'attempt 1/8'."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, gateway, telegram, debugging, messaging]
    related_skills: [systematic-debugging, hermes-agent]
---
# Hermes Gateway Debugging

The `hermes gateway run` process connects the agent to messaging platforms
(Telegram, Discord, WhatsApp, Slack, etc.). When a platform adapter hangs
or crashes at startup, the symptom is usually a frozen log line — not a
stack trace. This skill captures the highest-value root cause for the Telegram
adapter and a reusable technique for any gateway/platform issue.

## When to use
- `hermes gateway run` prints `Connecting to Telegram (attempt 1/8)…` and
  never reaches `Connected to Telegram`.
- A platform adapter logs a warning then goes silent.
- Messages aren't delivered even though the token is valid (verified via `curl`).
- A gateway crash loop on a specific platform.
- **WhatsApp: outbound `hermes send` works but the user's replies never reach
  the agent** (bridge shows `✓ whatsapp connected`, gateway.log has ZERO
  `inbound message: platform=whatsapp`). This is NOT a gateway hang — it's the
  bridge silently dropping `fromMe` messages. See the `whatsapp-setup` skill,
  section "Inbound delivery — why the bot's OWN replies never arrive".

## The #1 Telegram root cause: duplicate bot instance (409 Conflict)
The single most common "hang" is NOT a network bug. The gateway's Telegram
adapter calls python-telegram-bot's `get_updates` (long polling). If ANY
other process is already polling the same bot token, the new instance gets:
```
telegram.error.Conflict: Conflict: terminated by other getUpdates request;
make sure that only one bot instance is running
```
The gateway's connect loop catches this as "still trying" and the log freezes at
`Connecting to Telegram (attempt 1/8)…` with no error. It looks hung but
it's a 409 from a ghost instance.

**Fix:** kill every hermes/gateway process, then start exactly one instance.
```bash
ps aux | grep -iE "hermes|gateway" | grep -v grep
# kill them all, then:
hermes gateway restart
```

## Reusable technique: reproduce the adapter's exact call path in isolation
Don't guess which layer hangs. Rebuild the platform client exactly as the
gateway builds it, in the gateway's own venv, and call `initialize()` +
one real request. The error the gateway swallows will surface directly.

For Telegram the gateway venv is `~/.hermes/hermes-agent/venv/bin/python3`.
Repro recipe (also saved in `references/telegram-hang-repro.md`):
```python
import asyncio, os
from telegram.ext import Application
from telegram.request import HTTPXRequest
import httpx
os.environ["TELEGRAM_BOT_TOKEN"] = "bot<TOKEN>"
req = HTTPXRequest(connection_pool_size=512, pool_timeout=8.0,
    connect_timeout=10.0, read_timeout=20.0, write_timeout=20.0,
    httpx_kwargs={"limits": httpx.Limits(max_connections=512,
        max_keepalive_connections=10, keepalive_expiry=5.0)})
async def main():
    app = Application.builder().token(os.environ["TELEGRAM_BOT_TOKEN"]).request(req).build()
    await app.initialize()                       # <- hangs? network/transport
    await app.bot.get_me()                       # token valid?
    await app.bot.get_updates(timeout=5, limit=1)  # <- Conflict if 2nd instance
    await app.shutdown()
asyncio.run(asyncio.wait_for(main(), timeout=45))
```
Read the result:
- `initialize()` itself hangs → network/transport (see Pitfalls).
- `get_updates` raises `Conflict` → DUPLICATE INSTANCE (the real bug above).
- `get_me` raises `Unauthorized` → bad/expired token.

## Misdiagnosis trap: 'no delivery target' ≠ channels down
A cron job failing with `Delivery failed: no delivery target resolved for
deliver=all` does NOT mean the messaging channels are disconnected. It means
the JOB's `deliver` setting tried to fan out to `all` configured delivery
targets and the resolver found none *for that run* — commonly because the job
was previously set to `deliver=local` or the delivery targets were never
resolved at schedule time. The gateway and its channels can be perfectly
healthy. Verifying real channel state before "fixing" channels saves tokens
and avoids redundant setup steps.

**Correct diagnostic order (cheap, no tokens):**
```bash
# 1) Is the gateway even alive? (launchd/systemd supervised = always-up)
hermes gateway status            # shows PID, auto-start, auto-restart
hermes gateway list              # shows profile + PID per gateway
# 2) What did the channels actually DO recently? (proof of life, not assumption)
tail -n 50 ~/.hermes/logs/gateway*.log | grep -iE "telegram|whatsapp|agentmail|connected|inbound|response ready"
# 3) Which job carried the 'no delivery target' error, and what is its deliver mode?
hermes cron list                 # read Deliver: field per job
```
If `gateway status` shows a live PID AND the log shows `inbound message:
platform=whatsapp` / `Telegram polling restarted` / agentmail activity, the
channels are UP. The only fix needed is `hermes cron update <job_id>
deliver=all` (or whichever fan-out you want) — NOT re-running `hermes gateway
setup` or `whatsapp`. Re-running channel setup when channels are already
connected is pure wasted work.

**Transient network blips are normal, not failures.** Telegram logs
`polling degraded (heartbeat probe)` + `httpx.ConnectError` then
`polling restarted after network error (attempt N)` seconds later. That is a
~6-second network hiccup the adapter self-healed; do not treat it as a down
channel. Only act if the log shows *persistent* reconnect failure (attempt
≥10 with no restart) or a `Conflict: terminated by other getUpdates` (that is
the duplicate-instance bug above).

## Gateway alive but 'No messaging platforms enabled' — the platforms-disabled state
A running gateway does NOT mean any chat platform is connected. The macOS
launchd service `ai.hermes.gateway` keeps the CORE alive (cron, housekeeping)
even when zero platforms are enabled. Symptom:
- `hermes gateway status` → service supervised by launchd (live PID), but
- its log tail → `WARNING gateway.run: No messaging platforms enabled.
  Gateway will continue running for cron job execution.`
- `hermes config show` → `Telegram: not configured` / `Discord: not configured`.

This is a DISTINCT state from "service down". For this user the usual root
cause is that the platform-credential env file `~/.hermes/.env` is missing or
not loaded, so the adapters (Telegram token, WhatsApp bridge mode, etc.) never
initialize — even though `config.yaml` `platform_toolsets` lists
telegram/whatsapp (those entries only map toolsets, they do NOT enable the
adapter).

**Diagnostic (cheap, no tokens):**
- `hermes status --all` → read the `.env file:` line. `✗ not found` means the
  credential env is absent → that is why no platform connects.
- If `.env` exists, grep it for the enablement vars: `TELEGRAM_BOT_TOKEN`,
  `WHATSAPP_MODE`, `WHATSAPP_ENABLED`, `WHATSAPP_ALLOWED_USERS`,
  `DISCORD_BOT_TOKEN`. Absent/empty = platforms off.
- `hermes gateway status` shows the core PID but the log has NO
  `✓ telegram connected` / `✓ whatsapp connected` lines.

**Fix path:** restore/populate `~/.hermes/.env` with the platform credentials
(re-run `hermes whatsapp` for the bridge, or re-enter the Telegram token), then
restart the gateway (see Pitfalls — NOT from inside the gateway chat). If the
service itself is healthy and only platforms are missing, do NOT reinstall the
gateway; just fix the env file.

**Two layers of "configured":** `hermes config show` "Telegram: not configured"
reflects the *credential/env* layer, NOT the `platform_toolsets` in
config.yaml. A platform can show "not configured" yet still have a toolset
mapping. The actionable signal is the env layer.

## Pitfalls
- **Never restart the gateway from inside the gateway-served chat.** If the
  chat agent is itself running under the gateway process, killing the gateway
  kills your own session (the agent that issued the restart dies). The fix
  must be run in a SEPARATE terminal (Terminal.app / iTerm). From inside the
  served chat, just diagnose and tell the user the exact command to run
  elsewhere.
- **macOS has no `timeout` binary.** Wrap repro loops in
  `asyncio.wait_for(coro(), timeout=45)` instead of `timeout 45 cmd`.
- **Don't hand-edit `~/.hermes/config.yaml`** — use `hermes config set`.
  `.env` is for secrets only; behavioral flags belong in `config.yaml`.
- **`httpx.AsyncHTTPTransport` rejects `connect_timeout`/`read_timeout`**
  as kwargs — they belong on `HTTPXRequest` (which forwards them to the
  client), not on the transport. Passing them to the transport raises
  `TypeError: unexpected keyword argument 'connect_timeout'`.
- The gateway's Telegram `TelegramFallbackTransport` branch is selected
  whenever `discover_fallback_ips()` returns an IP (it queries Google/Cloudflare
  DoH). On networks where `api.telegram.org` is slow, that transport can
  wedge because it doesn't honor the request timeouts the way the plain path
  does. The simplest reliable fix is the single-instance one above; for
  network-specific wedging, the robust workaround is a code patch to propagate
  timeouts — prefer the upstream fix over editing installed code.
- Verify a bundled/installed skill is editable before writing to it; the
  `hermes-agent` skill is bundled (protected) and a curator-run writer will be
  refused. Capture Hermes-specific findings in a separate class-level skill
  like this one.

## References
- `references/telegram-hang-repro.md` — full repro script + step-by-step
  diagnosis used to confirm the duplicate-instance root cause.
