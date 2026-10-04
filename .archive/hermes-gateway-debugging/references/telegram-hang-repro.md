# Telegram Gateway Hang — isolated repro + step-by-step diagnosis

Used to confirm that `hermes gateway run` freezing at
`Connecting to Telegram (attempt 1/8)…` is a DUPLICATE BOT INSTANCE
(409 Conflict from a ghost gateway process), not a network/transport bug.

## Step 1 — token + network sanity (curl, same host)
```bash
curl -s -m 10 "https://api.telegram.org/bot<TOKEN>/getMe"
# expect: {"ok":true,"result":{"username":"elgriego_bot",...}}
```

## Step 2 — is another instance already polling the bot?
```bash
ps aux | grep -iE "hermes|gateway" | grep -v grep
# If anything shows, KILL ALL hermes/gateway processes, then:
hermes gateway restart
```
This alone resolved the reported case (a previous `hermes gateway`
background run that was killed but left a polling child).

## Step 3 — reproduce the gateway's exact PTB call path in isolation
Run with the gateway's own venv Python. NOTE: macOS has no `timeout`
binary — wrap in `asyncio.wait_for(..., timeout=45)` instead.

```python
import asyncio, os
from telegram.ext import Application
from telegram.request import HTTPXRequest
import httpx

os.environ["TELEGRAM_BOT_TOKEN"] = "bot<TOKEN>"

req = HTTPXRequest(
    connection_pool_size=512, pool_timeout=8.0,
    connect_timeout=10.0, read_timeout=20.0, write_timeout=20.0,
    httpx_kwargs={"limits": httpx.Limits(
        max_connections=512, max_keepalive_connections=10,
        keepalive_expiry=5.0)})

async def main():
    app = Application.builder().token(
        os.environ["TELEGRAM_BOT_TOKEN"]).request(req).build()
    await app.initialize()                 # <- hangs? => network/transport
    me = await app.bot.get_me()          # <- Unauthorized? => bad token
    print("get_me OK:", me.username)
    upd = await app.bot.get_updates(timeout=5, limit=1)  # <- Conflict? => dup instance
    print("get_updates OK updates=%d" % len(upd))
    await app.shutdown()

asyncio.run(asyncio.wait_for(main(), timeout=45))
```

## Reading the result
| Symptom in repro                    | Meaning                          | Action                          |
|------------------------------------|----------------------------------|---------------------------------|
| `initialize()` hangs >10s           | network / fallback transport wedge | single-instance fix first; see SKILL.md pitfalls |
| `get_updates` raises `Conflict`     | **duplicate bot instance** (the real bug) | kill all gateway procs; `hermes gateway restart` |
| `get_me` raises `Unauthorized`      | bad/expired token                | re-issue token in BotFather    |
| clean success                       | env/network fine; the hang was the dup instance | just restart single-instance |

## Confirmed facts (Hermes v0.19.0, PTB v22.6, macOS)
- `app.initialize()` alone succeeds in ~0.45s against a valid token.
- The wedge ONLY appears once a 2nd process polls the same bot.
- `HERMES_TELEGRAM_DISABLE_FALLBACK_IPS=true` does NOT skip DoH discovery
  in this build (the flag gates *use* of fallback IPs, not discovery), so it
  won't force the plain request path on its own.
- `httpx.AsyncHTTPTransport(**{"connect_timeout": ...})` raises
  `TypeError: unexpected keyword argument 'connect_timeout'` — those timeouts
  belong on `HTTPXRequest`, not the transport.
