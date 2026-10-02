---
name: google-workspace
description: "Connect Hermes to Google Workspace (Gmail, Calendar, Drive, Sheets, Docs, Contacts) via OAuth. Setup, credential recovery, token refresh, and auth-url/auth-code completion."
version: 1.1.0
author: Hermes Agent (curated)
license: MIT
platforms: [macos, linux, windows]
metadata:
  hermes:
    tags: [google, workspace, oauth, gmail, calendar, drive, sheets, docs, contacts, credential-recovery]
---

# Google Workspace Integration for Hermes

Use when the user wants Hermes to access Google Workspace services — "conectar Google", "reparar credenciales del drive", "actualizar archivo de movimientos", "refresh token google", or when Drive/Sheets/Calendar access is broken.

## Two entry points

**From-scratch setup** (`hermes google` / `$GSETUP`):
- Install deps: `$GSETUP --install-deps`
- Register client secret: `$GSETUP --client-secret ~/.hermes/google_client_secret.json`
- Generate auth URL: `$GSETUP --auth-url` → outputs URL, saves to `~/.hermes/google_oauth_last_url.txt`
- User opens URL in browser, grants consent, gets `code` → paste back.

**Credential recovery (existing Drive token → full Workspace):**
When only an old Drive token exists (e.g. `~/.hermes/contabilidad/drive_token.json`) but Drive (or full Workspace) access is broken:
1. Read the old token file — it contains `client_id` and `client_secret` embedded.
2. Build `~/.hermes/google_client_secret.json` from those two fields:
   ```json
   {
     "installed": {
       "client_id": "<from token>",
       "client_secret": "<from token>",
       "auth_uri": "https://accounts.google.com/o/oauth2/auth",
       "token_uri": "https://accounts.google.com/o/oauth2/token",
       "redirect_uris": ["http://localhost:1"]
     }
   }
   ```
3. Register with `$GSETUP --client-secret ~/.hermes/google_client_secret.json`
4. Generate auth URL: `$GSETUP --auth-url`
5. User completes browser flow, pastes `code`.

## Auth URL + code completion

- The auth URL is a `response_type=code` flow with `redirect_uri=http://localhost:1`.
- After the user approves in the browser, Google redirects to `http://localhost:1?code=<CODE>&...`.
- **If the browser "hangs"** after approval:
  - **Caso A** — the URL bar shows the full redirect with `code=...`. Copy the ENTIRE URL (including `code=`) and paste it. Do NOT wait for a page to load — there is no page.
  - **Caso B** — Testing mode: the OAuth client is in "Testing" state and the user's Google account is not a listed test user. Fix: go to https://console.cloud.google.com/auth/audience, add the user's email as a test user. Then retry.
- Once the code is pasted, `$GSETUP` exchanges it for tokens and writes `~/.hermes/google_token.json`.

## Token lifecycle

- Google OAuth tokens have a `expires_at` (epoch seconds). When expired, refresh with the stored `refresh_token`.
- Refresh command (if a manual refresh is needed): use the refresh_token from `google_token.json` to hit `https://oauth2.googleapis.com/token` with `grant_type=refresh_token`.
- A successful refresh updates `token`, `expires_at`, and `refresh_token` (sometimes rotated).
- If refresh fails (e.g. `invalid_grant`), the token is revoked — re-run the full auth URL → code flow.

## What to check when "Drive no funciona"

1. Read `~/.hermes/google_token.json` — is there a `token` field? Is `expires_at` in the past?
2. If expired, attempt refresh with refresh_token.
3. If refresh fails → token revoked → re-auth.
4. Test access: `curl -H "Authorization: Bearer <token>" https://www.googleapis.com/drive/v3/files?spaces=drive&fields=files(id,name)`

## Pitfalls

- **Do not lose the `refresh_token`** — it is the only permanent credential. The `token` (access token) is short-lived and refreshable. If `google_token.json` is deleted without a backup of `refresh_token`, full re-auth is required.
- **`google_client_secret.json` is NOT a token** — it is the OAuth client registration (client_id + client_secret). Keep it; it is needed for every re-auth.
- **Scope mismatch**: old Drive-only tokens have `https://www.googleapis.com/auth/drive`. Full Workspace needs additional scopes (Gmail, Calendar, Contacts, Sheets, Docs). Use `$GSETUP --auth-url` without `--services` to get the full scope set — the flag `--services all` is rejected.
- **Auth URL generation**: `$GSETUP --auth-url` without arguments generates the full scope URL and saves it to `google_oauth_last_url.txt`. Do NOT pass `--services all` — that flag does not exist.

## Files

- `~/.hermes/google_client_secret.json` — OAuth client registration (client_id + client_secret). RECOVERABLE from old Drive token.
- `~/.hermes/google_token.json` — live OAuth tokens (access + refresh).
- `~/.hermes/google_oauth_last_url.txt` — last generated auth URL.
- `~/.hermes/contabilidad/drive_token.json` — may contain embedded client_id + client_secret (source for recovery).

## References

- `references/credential-recovery.md` — step-by-step recovery when only an old Drive token exists.
- `references/token-lifecycle.md` — token expiry, refresh, and revocation handling.

## Related

- `whatsapp-setup` — for WhatsApp bridge setup (different domain).
- `homelab-wake-on-lan` — for WOL-based server power control (different domain).
