---
name: llm-cost-control
description: "Control Hermes LLM API spend and paid provider cost."
version: 1.0.0
author: Hermes Agent (session-derived)
license: MIT
platforms: [macos, linux, windows]
metadata:
  hermes:
    tags: [hermes, cost, budget, anthropic, openai, provider, guardrails, max_turns]
---

# Controlling LLM API Cost in Hermes Agent

Use when a user wants to use their own paid API key (Anthropic / OpenAI / …) "without it getting out of control", or asks how to cap spend.

## The core gotcha
`config.yaml` has **NO native dollar / spend / budget limit**. You cannot set "cut me off at $5/session" from Hermes. The hard ceiling must be set in the **provider's own console** (Anthropic usage limits, OpenAI usage limits, etc.). When a user fears runaway cost, the non-negotiable safety net is that provider-console limit — state it explicitly, don't imply Hermes caps it.

## Hermes-side controls (reduce load; they do NOT cap $)
- **Cheap model alias** — default to the smallest adequate model. e.g. `/model haiku` or `hermes config set model.aliases.fav anthropic/claude-haiku-3.5`. Do NOT default to opus/sonnet for routine tasks.
- **`agent.max_turns`** (default 150) — lower to ~60 to bound turns per session and avoid runaway loops.
- **`tool_loop_guardrails.hard_stop_enabled`** — set `true` (default `false` = warn only) to hard-stop tool loops after thresholds.
- **`compression.enabled`** (true) — keeps context small → fewer input tokens per turn.
- **`delegation.max_iterations`** (50) — bounds subagent iteration count.

## Context: default install is $0 for the LLM
Out of the box Hermes uses `tencent/hy3:free` via **Nous Portal (OAuth)** — free LLM calls. Managed tools (web, browser, image_gen, tts, stt) ride the Nous subscription. Cost only appears once you switch to a paid provider/model. To inspect: `hermes status` shows Model/Provider and which keys are set.

## Workflow
1. `hermes status` → confirm current model/provider and which API keys are configured.
2. Set a cheap default alias; lower `max_turns`; enable `hard_stop` guardrails; confirm compression is on.
3. Instruct the user to set a spend limit in the provider console — that is the real cap, not Hermes.

## Guarantee $0: make LOCAL Ollama the fallback (verified pattern)
Cheapest isn't just a free default — it's a fallback chain that NEVER reaches a paid provider. Working recipe (user's Mac Mini, Ollama `qwen3:8b`):

1. Keep default free: `hermes config set model.default tencent/hy3:free` (provider `nous`, $0).
2. Register ONLY the model Ollama actually has. Mismatch = silent cost leak:
   `hermes config set custom_providers '[{"name":"ollama-local","base_url":"http://localhost:11434/v1","api_key":"ollama","models":[{"name":"qwen3:8b","context_length":40960}]}]'`
   **GOTCHA:** if `custom_providers.models` lists a model Ollama does NOT have installed (e.g. `qwen2.5:7b`, `hermes3:8b`), the fallback request fails and Hermes falls through to the NEXT provider in the chain — usually a PAID one (Anthropic). Always `curl -s http://localhost:11434/api/tags` first and list exactly those names.
3. Fallback to local only; REMOVE paid providers from the auto chain:
   `hermes config set fallback_providers '[{"provider":"custom:ollama-local","model":"qwen3:8b"}]'`
   Keep Anthropic/OpenAI for explicit manual use only, never in the auto chain.
4. Verify the local endpoint answers:
   `curl -s --max-time 30 http://localhost:11434/v1/chat/completions -H "Content-Type: application/json" -d '{"model":"qwen3:8b","messages":[{"role":"user","content":"responde solo: OK"}],"max_tokens":10}'`
Result chain: `nous-free → ollama-local(qwen3:8b) → STOP`. If the Nous free pool drains (see below), it falls to local $0 instead of paid. Confirm: `hermes config get fallback_providers --json`.

## Cron jobs must also stay $0 and deliver cleanly
- A cron run inherits the parent model/fallback chain, so the $0 setup above applies to scheduled jobs too — no extra cost config needed inside the cron.
- **Pitfall: `deliver=all` fails with "no delivery target resolved" if no channel is connected.** Hermes declares Telegram/WhatsApp/mail as available toolsets but "declared ≠ connected" — if the user hasn't linked a channel, `deliver=all` has no target and the job errors (even though the job body ran OK). Until channels are connected, set the cron `deliver=local` (output saved to the job, no delivery error). Switch to `deliver=all` once the user links channels. Check via `cronjob list` → inspect `last_delivery_error` per job.

### Refinement: the Nous "free" model rides a shared credit/rate pool
`tencent/hy3:free` is $0 but served from Nous's shared credit/rate pool, not a limitless free tier. When that pool is exhausted (a user saw their session cut off mid-work), the free model stops answering until renewal — even though the model itself draws nothing from the managed-tool pool. The local-Ollama fallback is the ONLY way to keep working at $0 when the Nous pool is empty. Note: the session that hit this had `anthropic` listed as fallback AFTER an Ollama entry pointing at an uninstalled model — so a model-mismatch fallback silently leaked toward paid. Listing only installed local models prevents that.

## The Nous "free tool pool" (a second, separate cost surface)
When the user is on the default `tencent/hy3:free` model via **Nous Portal**, LLM conversation is $0 — but that is NOT the only thing that can cost. Managed tools ride the **free tool pool** (finite credits):
- **Funds (draws pool credits):** web search/extract (Firecrawl), browser automation, **image generation** (FAL/FLUX), and STT/TTS when routed through the gateway.
- **Does NOT fund:** video generation (denied for pool users).
- The model itself (`hy3:free`) does NOT draw the pool.

So "I'm on the free plan" is true for chat, but images/web/browser/voice can still exhaust the pool. Check balance at https://portal.nousresearch.com (or `hermes status` for entitlement).

### Route STT + TTS LOCAL to save the pool — without losing quality
The biggest easy win: keep voice I/O on the user's machine (free, $0, no pool draw, no cloud upload) while leaving image/web/browser on the gateway for quality.
- **STT (read voice notes):** `stt.provider: local` + `stt.use_gateway: false` → runs `faster-whisper` locally. Install: `pip install faster-whisper static-ffmpeg` (the `static-ffmpeg` package fetches a portable ffmpeg binary — no Homebrew/ffmpeg system install needed). Config in `config.yaml` → `stt.local.model: base` is a good speed/accuracy balance.
- **TTS (agent's voice out):** `tts.provider: edge` + `tts.use_gateway: false` → Microsoft Edge TTS, free, no API key, high-quality neural voices. Install: `pip install edge-tts`. Pick a voice e.g. `tts.voice: es-ES-AlvaroNeural`. (Alternative `piper` is 100% offline but sounds slightly more robotic.)
- **Keep image_gen / web / browser on the gateway** (FLUX/Firecrawl) for quality — but **warn the user before generating an image**, since that is the single largest pool drain.
- Concrete setup + verification commands: see `references/local-voice-no-pool.md`.
- Portable Ollama (no Homebrew/sudo) for a second local agent: `references/macos-portable-ollama.md`.

## Pitfall: 401/auth failures do NOT trigger the fallback chain
The fallback chain in `fallback_providers` fires on 429, 503, 529, connection
failures, and recognized billing-exhaustion messages — but **NOT on HTTP 401
authentication errors**. If the user's paid API key is revoked/expired/wrong,
the gateway keeps retrying the broken primary provider turn after turn, and
the conversation effectively dies. The agent sees only generic auth errors
in logs, not a "switch to fallback" notice.

**Diagnosis recipe when gateway chat is silent/broken:**
1. `tail -100 ~/.hermes/logs/errors.log | grep -E "(401|auth|invalid)"` —
   confirms if it's auth.
2. `hermes auth list` — each entry shows `auth failed authentication_error`
   next to a broken credential. That's the smoking gun.
3. **Fix:** either re-set the key (`hermes auth add <provider>`) OR rotate the
   primary model to a working one (`hermes config set model.default ...`).
   Do NOT assume the fallback chain will save you from a 401.

## Pitfall: `config.yaml` is AGENT-WRITE-PROTECTED
You CANNOT edit `~/.hermes/config.yaml` with `patch`/`write_file` — Hermes refuses ("Refusing to write to Hermes config file … Edit directly or use 'hermes config'"). Two paths:
- Preferred: `hermes config set <key> <value>` (e.g. `hermes config set stt.provider local`). For keys the running version doesn't recognize, append `--force`.
- If you must bulk-edit, tell the user to edit the file directly, or do it via `hermes config set` per key.
- After any `pip install` into the Hermes venv, the resolver may bump a transitive dep (seen: `packaging` 26.0 → 26.2). Re-pin to avoid breaking Hermes: `pip install "packaging==26.0"`.

## Local-first token-austerity PIPELINE (verified pattern)
When a user wants paid-API austerity WITHOUT losing the workflow or hitting resource starvation: split work by cost tier and gate the paid tier behind a state file + queue.
- **Routine work = local Ollama $0.** Parse/classify/extract with `qwen3:8b` (or similar) via `http://localhost:11434/api/generate` (set `stream:false`; the model emits a `reasoning`/`thinking` block — strip it, the real answer is in `response`). Never let the LLM do the *write* — it returns a structured draft (JSON) that deterministic code commits.
- **Paid API = authorized high-level only.** Reserve Claude/OpenAI for reconciliation decisions the user explicitly approves. Wrap every paid call behind `hay_credito()` so it can NEVER fire outside a recharge window.
- **Credit-state file** (`referencia/estado_creditos.json`): `{presupuesto_claude, usado_claude, ventana_recarga, umbral_ahorro}`. `hay_credito()` returns True only when `ventana_recarga` is on AND `(usado/presupuesto) < umbral`. Set `ventana_recarga=true` + `presupuesto` on recharge; turn off when drained.
- **Task queue** (`scripts/cola_claude.py`): `encolar` for anything that needs the paid API; `drenar` does nothing in savings mode and only lists due tasks when `hay_credito()` is True. This means the pipeline never stalls (local covers the routine) and paid spend is batched into the recharge window to "rendir la recarga".
- **$0 cron to drain** (`drenar_cola_claude.sh`, every 6h, `no_agent=true`): runs the drain check for free; in savings mode it's a no-op, on recharge it surfaces the queued tasks. Use `deliver=local` (no channel needed).
- **Preserve data, log clearly:** books are append-only (never delete a row — correct by adding + documenting in a CHANGELOG.md). Each automated registration appends one line to CHANGELOG via a marker token so future inserts stay ordered.
- Keep the paid key OUT of git (`.gitignore` excludes `drive_token.json`, `*.token.json`, `.env`, `venv/`). Prefer local-only git (no remote) for private finance data.
- Working recipe: see `references/local-austerity-pipeline.md`.

## The Nous credit pool (shared / recharge mechanics)
Nous Portal is OAuth, not a user-managed API key: the user "carga" credits (e.g. $5) into a Nous account and Hermes draws from that managed pool. The default `tencent/hy3:free` chat model is $0 but rides Nous's *shared* credit/rate pool that exhausts and renews on Nous's own cycle — a drained pool cuts off the free model even though chat itself costs nothing. Managed tools (web/browser/image/STT/TTS) draw a *separate* finite free-tool pool from the funded balance. Keep a local-Ollama fallback so a drained Nous pool never blocks work. Condensed Q&A: `references/nous-credit-pool.md`.

## Local model offload on macOS WITHOUT Homebrew / WITHOUT sudo
For a cost-sensitive user who wants a second local agent (e.g. Qwen) to offload work from the main model, Ollama installs portably with no system writes:
- Download `https://ollama.com/download/ollama-darwin.zip`, unzip; the binary is at `Ollama.app/Contents/Resources/ollama`. Run `ollama serve` in background, then `ollama pull qwen2.5:7b`.
- On an Apple M4 / 16 GB: Qwen2.5 7B (4.7 GB) runs at ~22 tokens/s generation, 250 tok/s prompt — fluid, $0, offline.
- 16 GB is the ceiling: 7B is the sweet spot; 14B+ competes for RAM with Hermes/whisper/tts.
- Reproducible recipe: see `references/macos-portable-ollama.md`.

## Pitfall: you CANNOT restart/stop the gateway from inside the gateway process tree
After editing `config.yaml` (e.g. flipping STT/TTS to local) you may want a clean restart. **This is blocked** if your shell is a descendant of the running gateway — on macOS the agent shell's PPID is the gateway PID, and the gateway is a launchd job (`ai.hermes.gateway`):
- `hermes gateway restart` / `hermes gateway stop` → blocked: *"cannot restart or stop the gateway from inside the gateway process … SIGTERM propagates to child processes."*
- `launchctl unload/load ~/Library/LaunchAgents/ai.hermes.gateway.plist` from inside the gateway → also blocked (sandbox detects gateway-tree origin).
- Even `setsid nohup <script> &` launched from the agent still inherits the block; writing a restart script and disowning it does not escape.
**Fix — the USER does it from a NORMAL terminal (not via the agent/WhatsApp), ~10s:**
```
launchctl unload ~/Library/LaunchAgents/ai.hermes.gateway.plist
launchctl load   ~/Library/LaunchAgents/ai.hermes.gateway.plist
```
or simply `hermes gateway restart` in a shell that is NOT a child of the gateway. The gateway stays connected meanwhile (WhatsApp/Telegram keep working on the old PID); the restart is preventive, not urgent. Do not loop retrying restart from the agent — tell the user to do it.

## Diagnostic: what models do I actually have available right now?
When a user asks "use model X for WhatsApp" but X isn't configured, don't just
say "X isn't available." Show the real options so they can pick:

```bash
hermes auth list                           # working/broken API keys + OAuth
curl -s http://localhost:11434/v1/models   # local Ollama models
hermes status                              # current default + which providers are configured
```

The output of these three commands gives a complete picture: which paid
providers are healthy, which are dead (401/billing), what runs locally for
$0, and what the gateway is currently defaulting to. Present this as a small
table and let the user choose — don't unilaterally pick.

## Pitfall: portable Ollama does NOT auto-start after reboot
`ollama serve` launched in background (even via the nohup recipe in `references/macos-portable-ollama.md`) dies on logout/reboot. For a cost-sensitive user who wants Qwen always available, install a **launchd plist** (~/Library/LaunchAgents/) that runs `<ollama-bin> serve` on login. Otherwise every reboot requires re-running `ollama serve` and the model isn't loaded until first use. Offer to write that plist (it's the natural follow-up to the portable install).
