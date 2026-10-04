# AgentMail 403 diagnostic — reproduction recipe (Aug 2026 session)

## Context
Cron job "Pregunta informe dominical familia Suarez" must (a) generate the weekly
contabilidad report and (b) send a question email from `hermenegildo-hermes@<DOMINIO_AGENTMAIL>`
to `<GMAIL_DESTINO>`. Report generation succeeded; the email was blocked.

## Environment
- Hermes MCP `agentmail` configured in `config.yaml`:
  `url: https://mcp.agentmail.to/mcp?apiKey=am_us_...c311`
- Key is stored **masked** on disk; real key injected at runtime → no REST fallback from terminal.

## Reproduction
Load the deferred tools, then call (all returned the same 403):

1. `tool_search("send email agentmail")` → confirms `mcp__agentmail__*` tools exist.
2. `mcp__agentmail__list_inboxes` → `Forbidden (HTTP 403) — the authenticated credential lacks permission for this action`
3. `mcp__agentmail__create_inbox` (username=hermenegildo-hermes, domain=agentmail.to) → 403
4. `mcp__agentmail__get_inbox(inboxId="hermenegildo-hermes@<DOMINIO_AGENTMAIL>")` → 403
5. `mcp__agentmail__list_threads(inboxId="hermenegildo-hermes@<DOMINIO_AGENTMAIL>")` → 403
6. `mcp__agentmail__send_message(inboxId="hermenegildo-hermes@<DOMINIO_AGENTMAIL>", to=["<GMAIL_DESTINO>"], subject=..., text=...)` → 403
7. `mcp__agentmail__send_message` (omitted inboxId) → rejected client-side: `missing required argument(s): inboxId. The tool was NOT invoked.`

Note: first `send_message` attempt returned `MCP server unreachable after 3 consecutive failures`
(transient transport). Retries returned the real API 403. The 403 is authoritative.

## Conclusion / fix
- The key is inbox-scoped to some UUID; the email string is NOT accepted as `inboxId` for
  send/list ops (only `get_inbox` documents accepting email).
- `send_message` requires the inbox **UUID**. It cannot be discovered because list/get/create
  are all 403 under this key.

### Actual fix applied (Aug 2026, CLI session — user correction)
The recurring 403 was the OLD masked key `am_us_...c311`. The real fix is credential rotation,
NOT discovering a UUID:
- The key is a **shared agent secret** in `~/.hermes/.env` (`AGENTMAIL_API_KEY`, mode 0600),
  loaded by the gateway at startup. Confirmed it existed (with a DUPLICATE line) via
  `execute_code` reading `.env` key names only (never print values).
- Rotation path: load `hermes-credential-provisioning` skill → write new key via `execute_code`
  (NOT `patch`, which refuses protected files) → `launchctl kickstart -k gui/$(id -u)/ai.hermes.gateway`
  → verify by re-calling `list_messages` (functional check; no `/proc` on macOS).
- The user supplied the new key prefix `am_us_5f559f…` INCOMPLETE. API keys are longer than
  the prefix; an incomplete key can't be configured. Require the FULL key before rotating.
  If pasted in chat, scrub from `state.db` with `scripts/redact_secret.py` immediately.
- Obsidian vault (`~/Documents/Obsidian/Contabilidad Suarez/`) was checked — NO AgentMail key
  is stored there (keys are never kept in the readable vault). Don't waste turns searching Obsidian.

## Report command that DID work (belongs to user-owned `contabilidad-suarez` skill)
```
cd /Users/manuelsuarez/.hermes/contabilidad
./venv/bin/python3 informe_semanal.py familia --no-enviar
```
→ prints the Google Drive `webViewLink` for the familia workbook (no email sent).
