# Credential Recovery for Google Workspace

Use when Drive (or full Workspace) access is broken and only an old Drive token exists.

## Situation

You have an old Drive token file (e.g. `~/.hermes/contabilidad/drive_token.json`) that contains:
- `client_id` (the OAuth client ID, e.g. `227459294501-xxx.apps.googleusercontent.com`)
- `client_secret` (embedded)
- possibly a `refresh_token` and expired `token`

The current `~/.hermes/google_token.json` may be missing, expired, or revoked. Goal: restore full Workspace access without creating a new OAuth client.

## Recovery procedure

1. **Read the old token file**: `cat ~/.hermes/contabilidad/drive_token.json`
2. **Extract `client_id` and `client_secret`** from the JSON.
3. **Write `google_client_secret.json`**:
   ```bash
   cat > ~/.hermes/google_client_secret.json <<'EOF'
   {
     "installed": {
       "client_id": "MICLIENT_ID_AQUI",
       "client_secret": "MICLIENT_SECRET_AQUI",
       "auth_uri": "https://accounts.google.com/o/oauth2/auth",
       "token_uri": "https://accounts.google.com/o/oauth2/token",
       "redirect_uris": ["http://localhost:1"]
     }
   }
   EOF
   ```
4. **Register the client secret**:
   ```
   $GSETUP --client-secret ~/.hermes/google_client_secret.json
   ```
   Expected output: `OK: Client secret saved`.

5. **Generate the auth URL**:
   ```
   $GSETUP --auth-url
   ```
   This writes the URL to `~/.hermes/google_oauth_last_url.txt` and prints it.

6. **User completes browser flow** — open the URL, grant consent, copy the `code` from the redirect URL.

7. **Paste the code** — the `$GSETUP` process or the assistant exchanges it for a fresh token.

## If the auth URL "hangs"

- **Caso A (code in URL)**: The browser redirects to `http://localhost:1?code=...`. Copy the FULL URL including `code=...` and paste it. The page doesn't load — that's normal.
- **Caso B (Testing mode)**: Google Cloud Console shows "Testing" for the OAuth client. Fix: add your email as a test user at https://console.cloud.google.com/auth/audience.

## Verifying the recovery

After getting the new token:
```bash
TOKEN=$(python3 -c "import json; print(json.load(open('~/.hermes/google_token.json'))['token'])")
curl -s -H "Authorization: Bearer $TOKEN" "https://www.googleapis.com/drive/v3/files?spaces=drive&fields=files(id,name,mimeType)"
```
A 200 with a file list confirms Drive access. Test Calendar with `.../calendar/v3/calendars/primary` and Gmail with `.../gmail/v1/users/me/profile`.

## If recovery fails

- `invalid_grant` on refresh → token revoked, re-auth required (go back to step 5).
- `access_denied` on auth URL → check test users (Caso B) or scopes.
- Cannot find `client_secret` → search the home directory: `grep -rl "227459294501" ~ 2>/dev/null` or `find ~ -name "*drive_token*" -o -name "*client_secret*"`.
