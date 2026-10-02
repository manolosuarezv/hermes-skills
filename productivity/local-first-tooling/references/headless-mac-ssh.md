# Headless Mac Mini over SSH (ThinkPad/Linux) — operating reality

Manuel drives the macOS Mac Mini **headless via SSH from a Linux ThinkPad**. This
changes which tools work for tasks that normally assume a local desktop.

## Hard constraint
macOS GUI permission prompts (System Settings ▸ Privacidad y seguridad ▸
Automatización / Automation) appear on the **physical Mac display**, NOT in the
SSH terminal. So any tool that needs a one-time GUI consent (e.g. the first
`osascript` that controls Mail.app) cannot be approved over SSH — it just hangs
until the popup is dismissed at the console. Don't build workflows that depend on
clicking a macOS dialog unless the user is physically at the Mac or uses Screen
Sharing (see below).

Detect the active GUI session:
```
who | grep -i console          # shows e.g. "manuelsuarez  console  Aug  4 ..."
```

## Email send, headless & $0 (preferred path)
Use `msmtp` + an app password. No GUI, no paid API, works 100% from SSH.

1. Install: `brew install msmtp`
2. Config `~/.msmtprc` (mode 600 — keep credentials OUT of any git repo):
   ```
   defaults
   auth           on
   tls            on
   tls_trust_file /opt/homebrew/etc/openssl/cert.pem   # or your CA bundle
   logfile        ~/.msmtp.log

   account        gmail
   host           smtp.gmail.com
   port           587
   from           tu-correo@gmail.com
   user           tu-correo@gmail.com
   # Gmail/Outlook REQUIRE an APP PASSWORD, not the account password:
   passwordeval   "cat ~/.msmtp-gmail-pass"            # file mode 600, app password only
   account default : gmail
   ```
   Store the secret in a separate 600 file (`~/.msmtp-gmail-pass`) referenced by
   `passwordeval` so it never sits inline in the config.
3. Send (message with To/Cc/Subject headers):
   ```
   cat borrador.md | msmtp -t            # -t reads recipients from the headers
   # or explicit:  msmtp destino@correo.com < borrador.txt
   ```

## Why NOT these for real delivery
- **`/usr/bin/mail` + postfix**: macOS postfix is local-only by default; it does
  NOT relay to external SMTP without configuring a smarthost. Reliable only for
  local mailbox delivery, not for reaching a real inbox.
- **himalaya**: good IMAP/SMTP CLI, but still needs the account configured
  (credentials file). Same $0/headless benefit as msmtp; pick whichever the user
  already has or prefers.

## Mail.app via AppleScript — Ruta B (one-time GUI approval, then headless)
Verified working on this Mac (2026-08-14): after the user clicked "Permitir" on
the Automation prompt at the physical console, an `osascript` send from SSH
delivered to a real Gmail inbox. Use this when msmtp isn't installed and the
user is willing to approve the prompt once at the Mac's screen.

Send (reads body from a file; strip any leading "Asunto:" line first):
```bash
open -a Mail 2>/dev/null; sleep 3
BORRADOR="$HOME/Documents/Obsidian/Contabilidad Suarez/Borrador Resumen Correo 2026-08-14.md"
DEST="USUARIO_GITHUB@gmail.com"
ASUNTO="Resumen familia Suarez - contabilidad local, austeridad y seguimiento (14 ago 2026)"
CUERPO=$(sed '1,/^Asunto:/d' "$BORRADOR" | sed '1d')
osascript -e "with timeout of 30 seconds
tell application \"Mail\"
  set nuevo to make new outgoing message with properties {subject:\"$ASUNTO\", content:\"$CUERPO\", visible:true}
  tell nuevo
    make new to recipient at end of to recipients with properties {address:\"$DEST\"}
    send
  end tell
end tell
end timeout"
# exit 0 + "true" on stdout = sent.
```
Pitfall: keep the message body free of bare double-quotes; if `$CUERPO` contains
`"` it breaks the AppleScript string. Plain text + escape if needed. Embedding a
multi-line variable across the `osascript -e` string is fine — the shell expands
`$CUERPO` before AppleScript sees it.

Verify it actually landed (do NOT trust exit 0 alone — a stuck outbox or the
first-run popup can swallow the send):
```bash
osascript -e 'with timeout of 25 seconds
tell application "Mail"
  set destAcct to first account whose name is "USUARIO_GITHUB@gmail.com"
  repeat with mb in (mailboxes of destAcct)
    try
      set msgs to (messages of mb whose subject contains "Resumen familia")
      if (count of msgs) > 0 then return "ENVIADO en mailbox[" & (name of mb) & "] -> " & (address of (to recipient 1 of msgs))
    end try
  end repeat
  return "NO_ENCONTRADO"
end tell
end timeout'
```
Gmail accounts: the sent copy lives in mailbox **"Sent Mail"** (NOT "Sent
Messages") AND is mirrored in **"All Mail"**. Iterate `mailboxes of account`
rather than hard-coding a mailbox name, because names are localized ("Enviados",
"Sent Mail", etc.).

### AppleScript syntax gotchas (cost real debugging time this session)
- The token `out box` / `outbox` triggers `syntax error: Expected "," but found
  identifier. (-2741)` inside `osascript -e`. To inspect the Outbox, do NOT
  reference it directly — confirm via the Sent / All Mail mailboxes instead, or
  iterate the account's mailboxes in a `repeat` loop.
- `out box` written as two words ALSO fails the same way; avoid it entirely in
  one-liners.
- `name of every mailbox of a` returns a list; coerce with `as string` before
  returning, or AppleScript errors on the return.
- A stray `,` or identifier where AppleScript expects a keyword (e.g. `out box`)
  is the classic `-2741`. Keep one-liners minimal; wrap multi-statement scripts in
  `with timeout ... end timeout` so a hung GUI call doesn't hang the SSH session.

## If a GUI truly is required (Screen Sharing / VNC)
Enable "Compartir pantalla" on the Mac (Ajustes ▸ Compartir). From the ThinkPad
use a VNC client (remmina/vinagre) → `vnc://<mac-ip>`. Then GUI prompts can be
clicked once. After that, headless SSH commands that previously needed the
permission will work. Use only as a one-time bootstrap, not as the steady state.

## Reused this session
Contabilidad familia Suárez: needed to email a summary draft. No mailer CLI was
installed (no msmtp/himalaya/mutt); Mail had a Gmail account but Automation
permission is GUI-bound. User chose Ruta B — powered on the Mac Mini monitor,
clicked "Permitir" on the Automation prompt at the physical console, gave the
destination `USUARIO_GITHUB@gmail.com`, and the AppleScript send delivered
(sent copy confirmed in both "Sent Mail" and "All Mail" of that account). Draft
left in the Obsidian vault at
`~/Documents/Obsidian/Contabilidad Suarez/Borrador Resumen Correo 2026-08-14.md`.
