---
name: hermes-send-outbound
description: Hermes send --to scripting; positional form silently fails.
---

# hermes-send-outbound

Use when a script (cron job, launchd plist, Python `subprocess`, shell pipeline) needs to push a notification out through the Hermes gateway to a messaging platform the user already configured. NOT for inbound messages — see `inbound-voice-messages`. NOT for initial WhatsApp pairing — see `whatsapp-setup`.

## The one rule that bites everyone
**`hermes send` requires `--to`. The positional form `hermes send <platform> "text"` is a SILENT FAILURE: it prints a usage error and delivers nothing.**

- ✅ `hermes send --to telegram "deploy done"`
- ✅ `hermes send --to whatsapp "alert"`
- ❌ `hermes send telegram "deploy done"`  → `usage: hermes send ...` printed, rc=0, nothing sent
- ❌ `hermes send whatsapp "alert"`  → same trap

From Python `subprocess.run(["hermes","send",canal,texto])` the positional form also dies. Build the argv as `["hermes","send","--to",canal,texto]`.

## Standard invocation (from a script)
```bash
hermes send --to telegram "message text"
echo "alert" | hermes send --to telegram:CHAT_ID   # piped body
hermes send --to telegram --subject "[CI]" --file /tmp/report.md
hermes send --to telegram "MEDIA:/tmp/chart.png"    # attach a file
```
Flags: `-t/--to TARGET` (format `platform`, `platform:chat_id`, `platform:chat_id:thread_id`, `platform:#channel`); `-f/--file`; `-s/--subject`; `-l/--list`; `-q/--quiet`; `--json`.
Exit codes: `0` ok, `1` delivery/backend error, `2` usage error.

## Discover what platforms are actually configured
`hermes send --list` prints only the platforms with credentials wired into `~/.hermes/config.yaml` + `.env`. If a platform is absent from that list, sending to it fails with `Platform 'email' is not configured`.
- In the contabilidad session, `hermes send --list` showed only `telegram` (dm "M S") and `whatsapp` (dm "."). `email` was NOT configured → every dispatch to email was silently dropped (caught by the try/except, never delivered).
- **Always rely on `--list` as the source of truth for "is channel X up", not on channel_directory.json alone.**

## WhatsApp home-channel caveat
`hermes send --to whatsapp` (bare, no chat id) needs a home channel. Setting it via `hermes config set WHATSAPP_HOME_CHANNEL <id>` works at send time BUT Hermes warns `"WHATSAPP_HOME_CHANNEL" is not a recognized config key — it was saved anyway, but Hermes may not read it.` So the key is fragile. Safer: pass the chat id explicitly, e.g. `hermes send --to whatsapp:132250767200321@lid`. For scripted dispatch where you must use bare `--to whatsapp`, set the home channel and verify with a probe send.

## Resilience pattern (use this in any parent job)
A missing/down channel must NOT abort the caller (e.g. a nightly accounting close). Wrap each channel in try/except and continue:
```python
def despachar(texto):
    if os.environ.get("HERMES_DISPATCH") != "1":
        return
    import subprocess
    for canal in ("telegram", "whatsapp", "email"):
        try:
            r = subprocess.run(["hermes","send","--to",canal,texto],
                               capture_output=True, text=True, timeout=30)
            if r.returncode != 0:
                sys.stderr.write(f"[digest] {canal} no disponible: {r.stderr.strip()[:120]}\n")
        except Exception as ex:
            sys.stderr.write(f"[digest] {canal} error: {ex}\n")
```
This was the fix that made `digest_diario.py` actually deliver to Telegram/WhatsApp after the positional-form bug.

## Verification recipe (cheap, before trusting a script)
1. `hermes send --list` → confirm target platform present.
2. `hermes send --to <platform> "probe $(date +%H:%M)"` → expect `Sent to <platform> home channel (chat_id: ...)`.
3. If bare `hermes send <platform> "x"` is ever used, replace with `--to`.

## Environment notes
- Gateway must be up for delivery. Check: `hermes gateway status` (launchd plist `ai.hermes.gateway.plist`, PID shown if running).
- `hermes send` reuses gateway credentials from `~/.hermes/.env` + `config.yaml`; it does NOT need a running gateway for bot-token platforms (Telegram/Discord/Slack/Signal) but WhatsApp typically routes through the gateway.
- No LLM / no agent loop is invoked by `hermes send` — it is a pure dispatch, safe to call from cron/launchd.

## Gotchas checklist
- [ ] Using `--to` (not positional) in every argv.
- [ ] Confirmed platform in `hermes send --list` (email is often unconfigured).
- [ ] WhatsApp home channel set OR explicit `whatsapp:CHAT_ID`.
- [ ] Parent job wraps each channel in try/except so one failure doesn't kill the run.
- [ ] Tested with a real probe send, not assumed.
