---
name: agentmail-mcp
description: "AgentMail MCP email: send requires inbox UUID, not address."
---

# AgentMail MCP

Use when you must send or read email through the AgentMail MCP server (`mcp.agentmail.to`), e.g. from an agent inbox like `hermenegildo-hermes@<DOMINIO_AGENTMAIL>`. AgentMail gives each agent an inbox on the `agentmail.to` domain; you drive it via MCP tools (loaded on demand with `tool_search` → `tool_describe` → `tool_call`).

## Tool inventory (mcp__agentmail__*)
- `list_inboxes` — list inboxes. Org/admin op; needs an **org-scoped** key.
- `create_inbox` — create inbox with custom `username@domain`. Needs org-scoped key.
- `get_inbox` — get inbox by **ID OR email** (accepts `username@agentmail.to`).
- `list_threads` — list threads in an inbox. Requires `inboxId`.
- `get_thread` — get a thread by `threadId`.
- `send_message` — **send** email from an inbox. Requires `inboxId` + `to[]`.
- `create_draft` / `update_draft` / `delete_draft` / `send_draft` / `list_drafts`.
- `reply_to_message` / `forward_message`.
- `list_organizations` / `select_organization` — **OAuth only**; with API-key auth these return an error ("organization selection does not apply to API-key authentication"). Don't waste a call on them under API-key auth.

## CRITICAL: `inboxId` must be the inbox UUID, not the email
- `send_message`, `list_threads`, `get_thread` require `inboxId` = the inbox **UUID** (e.g. `cm_xxx` / 24-char hex), NOT `username@agentmail.to`.
- Passing the email as `inboxId` returns `HTTP 403 — the authenticated credential lacks permission for this action`, **even though `get_inbox` accepts the email form**. The 403 here is misleading: it is not "bad password", it is "you passed an identifier the send/read path can't resolve under this key's scope."
- `send_message` enforces `inboxId` as a required schema param — you cannot omit it and rely on a default-scoped inbox.

## Diagnostic: HTTP 403 on MCP inbox operations
Before concluding that the AgentMail credential lacks access, test the direct REST API with the current `AGENTMAIL_API_KEY` and print only status plus redacted metadata. A REST `200` means the provider key works; the MCP process may have cached an older key, or the MCP path may require the UUID even when REST accepts the email address.

If the direct REST call also returns 403 and `list_inboxes`, `create_inbox`, `get_inbox`, `list_threads`, and `send_message` fail:
1. The configured API key is **inbox-scoped** (or otherwise narrowly scoped) → it cannot list/create/get inboxes, so you cannot *discover* the UUID.
2. The only path to send is to **already know the inbox UUID** and pass it to `send_message`.
3. To obtain the UUID you need an org-scoped / admin key (`list_inboxes` / `get_inbox`). The scoped key cannot give it to you.
4. Verify the inbox `username@agentmail.to` was ever created. If `create_inbox` is also 403, the key cannot create it → the inbox likely does not exist yet or belongs to a different scope.

## API key / REST fallback
- The AgentMail MCP `url` in `config.yaml` embeds `?apiKey=...`, but Hermes **stores the key masked on disk** (e.g. `am_us_...c311`). Do not search the masked config for a usable key.
- When `AGENTMAIL_API_KEY` is provisioned in `~/.hermes/.env`, use a short Python subprocess or `curl` call that reads it from `.env` without printing it. Verify only HTTP status and redacted metadata; never print the bearer token or full API-key response.
- REST base: `https://api.agentmail.to`. Useful org/inbox endpoints include `GET /v0/api-keys`, `GET /v0/inboxes`, and `GET /v0/inboxes/{inboxId}/messages`. The REST messages endpoint accepts the inbox email address; this does not change the MCP requirement that inbox-scoped tools receive the inbox UUID.
- Use the direct REST API to distinguish a stale MCP credential/cache from a bad key: a successful REST request with the current `.env` key proves the provider credential works, while an MCP 403 can still indicate cached or incorrectly scoped MCP state.

## FIXING A 403: rotate the API key in `.env` + restart the gateway
When ALL inbox ops 403 (list/get/create/threads/send), the key is effectively
read-restricted (inbox-scoped without send/read permission). The fix is NOT just
"get an org key" — the key is a **shared agent secret** provisioned via
`hermes-credential-provisioning`: it lives in `~/.hermes/.env` as `AGENTMAIL_API_KEY`
(mode 0600), which the **gateway** loads at startup. So:
1. Load skill `hermes-credential-provisioning` **first** — do NOT go greping the disk
   for `am_us_` (the key is masked on disk and the search wastes turns).
2. Replace `AGENTMAIL_API_KEY` in `~/.hermes/.env` with the new key. Use `execute_code`
   (Python, not `patch` — `.env` is a protected credential file and `patch` refuses it).
   De-dupe: the file may contain `AGENTMAIL_API_KEY` TWICE — collapse to ONE line.
   Never inline the raw key in a tool-call string; read it from a temp file or `.env`.
3. Restart the gateway so agents pick up the new env:
   `launchctl kickstart -k gui/$(id -u)/ai.hermes.gateway`
4. Verify FUNCTIONALLY (macOS has no `/proc`, can't read another process's env):
   re-call `list_messages` / `list_threads`. If 403 persists, the new key is also
   scoped wrong — get one with inbox send/read permission for `hermenegildo-hermes@<DOMINIO_AGENTMAIL>`.
5. If the key arrived via chat, immediately scrub it from history:
   `scripts/redact_secret.py ~/.hermes/state.db <KEY>` (it lands in `state.db` and the
   gateway's failure-recovery can re-emit it).

## Pitfalls
- Don't misread the send 403 as a transport error. The first attempt may show `MCP server unreachable` (transient); retries then return the real API 403. The 403 is the authoritative answer — stop retrying and diagnose scope.
- Don't hunt for the key with `search_files` / `grep` over `~/.hermes` — it's masked and
  the credential lives in `.env`. Go straight to the credential-provisioning workflow.
- `select_organization` errors under API-key auth; skip it.
- Don't use `list_threads` to "find" the inbox; it also needs the UUID.

## References
- `references/403-diagnostic.md` — reproduction recipe + error transcripts from the Aug 2026 session (report generated, email blocked by 403).
