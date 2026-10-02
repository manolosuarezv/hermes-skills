---
name: hermes-runtime-config
description: "Switch Hermes model/provider/fallback via `hermes config`."
version: 1.0.0
author: Hermes Agent (session-derived)
license: MIT
platforms: [macos, linux]
---

# Hermes Runtime Config (model / provider / fallback)

Use when the user wants to change the default model, set a fallback chain
(e.g. local Ollama when cloud credits run out), switch provider, or hits a
"cannot modify config" / "cannot restart gateway" error.

## CRITICAL — agent cannot edit config.yaml directly
Edits to `~/.hermes/config.yaml` via write/patch are BLOCKED by a security
guard. Always use the CLI:

```
hermes config set <dotted.key> "<value>"
hermes config get <dotted.key>      # verify
hermes config check                 # validate shape
```

## Set default model + provider
```
hermes config set model.default "tencent/hy3:free"
hermes config set model.provider "nous"
```
Nous Portal free model `tencent/hy3:free` uses the user's existing OAuth —
no API key needed.

## Set a fallback chain (cloud → local → OpenCode Free)
Auto-triggers on provider credit exhaustion, 429, 529, 503, or connection
failure. The list contains `provider:` + `model:` dicts and is tried in order.
For a complete chain, set the whole list in one CLI call rather than editing
`config.yaml` or relying on picker navigation:

```
hermes config set fallback_providers '[{"provider":"nous","model":"deepseek/deepseek-v4-flash-0731"},{"provider":"custom:ollama-local","model":"qwen3:8b"},{"provider":"opencode-free","model":"deepseek-v4-flash-free"}]'
hermes config get fallback_providers
hermes fallback list
```

`opencode-free` is anonymous and needs no API key. The global
`fallback_providers` chain applies to every messaging channel unless a session
or channel has its own model override. Fallback configuration is read on new
turns; restart the gateway when already-running messaging workers must be
certain to reload the runtime config.

## Per-platform model overrides
`channel_overrides` keyed by `chat_id` (also `thread_id`/`parent_id`) under
`platforms.<name>` pin a model/provider to one platform (e.g. WhatsApp only).
See `gateway/config.py` `ChannelOverride`.

## Audit — which model is each channel ACTUALLY using?
`hermes config get model.default` does NOT answer this. A `/model` switch
inside a session is **session-scoped**: it swaps the running session in place
and is NOT written to `config.yaml`, so a channel can be visibly running
model B while the global default still reads model A. Never report the config
value as "what channel X uses". Check in this order:
1. `hermes config get model.default` + `model.provider` — the global default,
   which applies to any session with no override of its own.
2. `~/.hermes/cron/jobs.json` (or `hermes cron list`) — cron jobs carry their
   own `model`/`provider` pin and do NOT follow the global default.
3. `~/.hermes/state.db` (sqlite3) — per-session truth: `gateway_routing`
   (`model_override` JSON per chat), `sessions` (`.model` = what ran last),
   `session_model_usage`.
4. Logs — the single line that states what actually ran:
   `grep -ah "conversation turn:" ~/.hermes/logs/agent.log` →
   `session=… model=… provider=… platform=whatsapp|telegram`; plus
   `grep -ah "Rehydrated persisted /model override" ~/.hermes/logs/gateway.log`
   for overrides re-applied at gateway start.
5. `hermes fallback list` — the chain, i.e. what runs when a primary fails.

Exact commands/SQL and the reporting rules: `references/channel-model-audit.md`.

**No "mail" channel exists.** AgentMail is an MCP toolset, not a platform with
its own model; mail is produced by whichever session/cron calls the tool —
answer by naming those sessions' models, not a nonexistent channel config.

**Subscription ≠ cheaper bill.** Changing model inside a Nous Portal
subscription does not lower the monthly charge, it only stretches the credits.
State this whenever the user expects switching models to reduce what they pay.

## Pitfall — use `hermes config set`, not direct file edits
The picker-based `hermes fallback add` requires a real TTY and is awkward for
repeatable automation. Do not bypass the config security guard with a Python
text replacement: set the complete `fallback_providers` list through
`hermes config set`, then verify with both `hermes config get fallback_providers`
and `hermes fallback list`. Order matters because entries are tried in list
order.

## Pitfall — cron jobs "fail closed" after a model.default change
`hermes config set model.default ...` prints a warning if any ENABLED cron
job has an unpinned `model_snapshot` differing from the new global model.
Those jobs will refuse to run on their next tick with:
`RuntimeError: Skipped to prevent unintended spend: global inference config
drifted ... this job is unpinned` — this is a deliberate safety guard, not a
bug. Fix by explicitly pinning each affected job's model/provider:
```
hermes cron edit <job_id> --provider nous --model upstage/solar-pro4:free
```
IMPORTANT: the agent-facing `cronjob` tool's `action=update` CANNOT set
model/provider (returns "No updates provided" if you try with no other
field) — pinning model/provider is user-owned and only works via the
`hermes cron edit --model --provider` CLI. Check `hermes cron list` for the
exact drift warning and job IDs; a job only "fails closed" the first time it
fires after the drift, so check `last_status`/`last_error` after a config
change, don't assume silence means success.

## Fallback also covers billing/credit exhaustion, not just rate limits
`agent/error_classifier.py`'s `_BILLING_PATTERNS` list recognizes provider
credit-exhaustion messages (Anthropic's "credit balance is too low" HTTP 400,
OpenAI's "insufficient_quota", etc.) and marks them `should_fallback=True` —
so a configured `fallback_providers` chain DOES catch "ran out of paid
credits," not just 429/503/529. Useful when a user wants "use paid model X
until credit runs out, then fall back to free model Y" — just configure the
fallback chain, no extra billing-detection logic needed.

## Fallback is per-turn, not permanent
Each new user message restarts on the PRIMARY model. If primary fails
mid-turn, fallback activates for that turn only; the next message tries
primary again first. There is no built-in "switch permanently to the
fallback until credit is topped up" mode — every subsequent turn re-attempts
(and re-fails) against the exhausted primary before falling back again. If a
user wants a hard, sticky switch instead of this repeated-retry behavior,
that requires an external watchdog (e.g. a cron job checking for the billing
error pattern and then running `hermes config set model.default ...`) — say
so explicitly rather than implying the fallback chain alone achieves it.

## Pitfall — cron execution status can stay "running" forever after the job actually finished
Hermes tracks each cron firing in `~/.hermes/cron/executions.db` (`status`,
`pid`, `finished_at`). For a long-running job (shell script doing WOL, SSH,
scp, remote shutdown), the tracked `pid` can exit and the row can stay stuck
at `status='running'`/`finished_at=NULL` indefinitely — the scheduler doesn't
always reap and record completion. **Do not conclude the job is hung or
failed from `hermes cron runs <job_id>` / the executions table alone.**
Verify against the job's REAL side effects instead:
- Remote file timestamps (`ssh ... 'ls -la <path>'`) or `git log -1` on the
  target repo for backup jobs.
- `ping` the target host to confirm it came up / shut down as expected.
- The job's own log file if it writes one (e.g. `/tmp/<name>_$(date +%Y%m%d).log`).
If the side effects confirm the work completed, the job succeeded even
though Hermes still shows it "running" — this is a tracking artifact, not a
task failure. See `qbex-contabilidad-backup` for a concrete worked example
(WOL backup script whose completion had to be confirmed via remote git log
+ ping, independent of the stuck cron status).

## Model choice for messaging-channel tasks with vision + tool-calling (e.g. WhatsApp receipts/OCR)
When a user wants a specific channel (WhatsApp, Telegram, etc.) to handle
image/PDF receipts plus follow-up tool actions (saving files to a remote
server, bookkeeping), and is cost-conscious about paid-provider credit:
- Default recommendation: a fast "haiku"-class model of whatever paid
  family the user already trusts for tool-calling reliability (e.g.
  `anthropic/claude-haiku-4.5` via Nous Portal, no separate API cost) — good
  vision, same tool-calling lineage as the heavier model, 4-5x cheaper/faster,
  appropriate for high-frequency conversational use.
- Alternative when scan/photo quality is poor (blurry receipts, small print):
  a flash-tier Gemini model (e.g. `google/gemini-3.7-flash`) tends to be
  stronger specifically at OCR-style extraction from low-quality images.
- Apply the choice via a per-platform `channel_overrides` entry (see above)
  rather than changing the global `model.default`, so the CLI/other channels
  keep their own model.

## User-style rule for model-selection replies (Manuel)
- **Always keep responses short, clear, and concrete.** The user has
  repeatedly asked: *"mantén las respuestas con poco texto, claras y concisas
  por favor"*. When recommending a model, present a compact table (3–5 rows
  max: modelo, contexto, precio, por qué) and end with 2–3 ready-to-paste
  CLI commands — not a long narrative. Do not narrate the diagnostic process,
  the failed attempts, or the API call internals; just state the verdict.
- **Lead with the verdict, not the diagnosis.** "Use X because Y" beats
  "I ran several commands, here is what they showed, so I think we should
  use X." The user can re-ask for detail if needed.

## Workflow — recommend a model for a specific channel
When the user asks "which of my available models is best for channel X
doing task Y":
1. **Show real options, never invent.** Run the three diagnostic commands
   (`hermes auth list`, `curl -s http://localhost:11434/v1/models`,
   `hermes status`) and present the output as a small table. If a provider
   is broken (e.g. Anthropic 401, Nous free saturated), say so plainly —
   do not paper over it.
2. **State the verdict first.** Pick one primary recommendation + one
   free fallback, with a one-line justification each (vision? tool-calling?
   context length? price?).
3. **Give ready-to-paste CLI for both.** Two blocks: (a) primary model via
   `hermes config set model.default` or `channel_overrides`, (b) fallback
   via `fallback_providers`. End with the `launchctl kickstart -k` restart
   line. Total reply ≤ 25 lines.

## Pitfall — Nous Portal subscription models require `curl` against `inference-api.nousresearch.com`
`hermes models` lists models ONLY for providers whose API key is in
`~/.hermes/.env`. For Nous Portal OAuth users, the **subscribed model list**
lives at `https://inference-api.nousresearch.com/v1/models` (NOT in `hermes
models`). To enumerate what the user's plan actually includes, extract the
Nous token with `grep NOUS_API ~/.hermes/.env | cut -d= -f2` and curl
that endpoint with `Authorization: Bearer <token>`. The response shape is
`{"data": [{"id": "...", "context_length": ..., "pricing": {...}, "architecture": {"input_modalities": [...]}}, ...]}`.

## Restart a model default change from a NON-gateway shell
The gateway restart is blocked from inside the gateway (see
`hermes-gateway-ops`). From a separate shell (Terminal.app on the Mac, or
SSH from another machine), the cleanest one-liner that reloads the plist
without juggling unload/load:

```
launchctl kickstart -k gui/$(id -u)/ai.hermes.gateway
```

`-k` first kills the running instance, then the same `kickstart` relaunches
it from the existing plist — equivalent to `unload && load` but atomic and
idempotent. Verify with `launchctl list | grep ai.hermes.gateway` (look for
a fresh PID). After the restart, the new `model.default` applies to all
subsequent sessions; already-open sessions cache their prefix and may need
a `/clear` or new session.

## Pitfall — gateway restart blocked in-session
Running `launchctl unload/load ai.hermes.gateway` from inside the gateway
(incl. the agent's own terminal tool) is BLOCKED: the gateway SIGTERMs its own
children and kills the command. Restart from a SEPARATE external shell
(Terminal.app), NOT from chat:

```
launchctl unload ~/Library/LaunchAgents/ai.hermes.gateway.plist
launchctl load   ~/Library/LaunchAgents/ai.hermes.gateway.plist
```

## Verify
- `hermes config get model.default` → new model.
- `hermes config get fallback_providers` → shows the chain.
- Only already-open sessions need the restart for a new primary model;
  fallback + channel_overrides are picked up live.
