# Secret leak recovery — Hermes state.db

## Root cause
When a raw secret (token/PAT) is pasted into a Hermes chat (Telegram/WhatsApp/CLI),
it is stored in the session transcript and persisted to `~/.hermes/state.db`:
- `messages.content`, `messages.api_content`
- `delivery_obligations.content`
- `gateway_routing.entry_json`
- `async_delegations.event_json` / `result_json` / `task_json`

On a transient model-provider failure, the gateway's recovery path re-emits
conversation context. If the secret is still in the transcript, it gets re-sent to
the user's chat. Observed live: a full `github_pat_…` appeared in a WhatsApp bubble
right after a "model provider failed after retries" + "Self-improvement review /
Memory updated" sequence.

The secret is NOT in `MEMORY.md`, the skills, or `~/.hermes/.env` — only in the
session `state.db`. The `.env` vault is isolated (0600) and was never the leak.

## Remediation (do in order)
1. **Revoke at the provider** (mandatory). GitHub: Settings ▸ Developer settings ▸
   Fine-grained tokens ▸ revoke. The chat/cloud copy is already compromised.
2. **Scrub `state.db`** (backup + redact + FTS rebuild):
   ```
   python3 scripts/redact_secret.py /Users/manuelsuarez/.hermes/state.db <LEAKED_SECRET>
   ```
   The script backs up to `state.db.bak_preredact`, redacts the secret from every
   table above, rebuilds the FTS5 indexes, and reports remaining matches (should be 0).
3. **Optional**: ask the user to delete the offending bubble in their phone chat to
   clear the cloud copy. This is secondary — step 2 protects the local agent; step 1
   protects the account.

## Rotation (new token via chat)
When the user sends a NEW token to replace the leaked one:
- Validate: `curl -sH "Authorization: Bearer <tok>" https://api.github.com/user`
- Write `.env` (`GITHUB_TOKEN=…`), `.git-credentials` (`https://x-access-token:<tok>@github.com`, 0600),
  `git config --global credential.helper store`, `gh auth login --with-token < /tmp/ghtok`.
- Then immediately `scripts/redact_secret.py` the NEW token from `state.db` so the
  replacement does not become the next leak.
- Restart the gateway (`launchctl kickstart -k gui/$(id -u)/ai.hermes.gateway`) so
  connected agents reload `.env`.

## FTS rebuild detail
The `messages_fts` / `messages_fts_trigram` tables are FTS5 virtual tables with
shadow tables. A `'delete'` insert corrupts them. Correct rebuild:
```sql
DROP TABLE IF EXISTS messages_fts;        -- + _data _idx _docsize _config
DROP TABLE IF EXISTS messages_fts_trigram;-- + _data _idx _docsize _config
CREATE VIRTUAL TABLE messages_fts USING fts5(content, tool_name, tool_calls, content='messages', content_rowid='id');
CREATE VIRTUAL TABLE messages_fts_trigram USING fts5(content, tool_name, tool_calls, content='messages', content_rowid='id', tokenize='trigram');
INSERT INTO messages_fts(messages_fts) VALUES('rebuild');
INSERT INTO messages_fts_trigram(messages_fts_trigram) VALUES('rebuild');
```
