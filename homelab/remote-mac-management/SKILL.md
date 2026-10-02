---
name: remote-mac-management
description: "Manage a headless Mac Mini remotely via Tailscale."
version: 1.0.0
author: Hermes Agent (session-derived)
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [macos, tailscale, remote, ssh, screen-sharing, homelab, mac-mini]
---

# Remote Mac Management (headless Mac Mini via Tailscale)

Use when the user is NOT physically at the Mac (different network, different location) and wants Hermes to drive it remotely — install apps, enable SSH/Screen Sharing, run privileged commands. The Mac Mini in play: Apple M4, 16GB, macOS 26.x, user `manuelsuarezv`, reachable via Tailscale.

## Reality check — what you CAN and CANNOT do remotely
- ✅ Run ordinary (non-sudo) terminal commands through the agent's terminal tool.
- ✅ Check Tailscale state, list peers, read files, run Homebrew (non-privileged), probe services.
- ❌ **Gain sudo automatically.** The framework blocks `sudo -S` (pipe a password = flagged as brute-force) AND `SUDO_PASSWORD` in `.env` does NOT make `sudo -n` work — the framework still requires interactive user approval. Do not waste turns trying to self-elevate.
- ❌ Click GUI dialogs (e.g. Tailscale "Allow" extension prompt in System Settings → Privacy). No Screen Sharing = no GUI. This is a hard chicken-and-egg: you need Tailscale for remote access, but approving its network extension needs a physical click.

## Verify Tailscale is installed + logged in
The cask install puts the CLI INSIDE the app bundle, NOT on PATH. Use the bundle binary:

```bash
# app present?
ls /Applications/Tailscale.app

# CLI binary (NOT on $PATH after cask install):
/Applications/Tailscale.app/Contents/MacOS/tailscale status
```

`tailscale status` prints peers with their Tailscale IPs and online state, e.g.:
```
100.101.1.51   HOSTNAME_MAC  USUARIO_GITHUB@  macOS  -
100.81.145.2   apple-tv            USUARIO_GITHUB@  tvOS   idle; offers exit node
100.112.175.96 iphone-15           USUARIO_GITHUB@  iOS    offline, last seen 110d ago
```
A line for the Mac with no `offline` suffix = connected. No `utun`/`tun` process + a peer list still printing = app installed but network extension possibly not approved yet.

## Cross-host SSH via Tailscale
When the user is connected to the Mac Mini from a laptop but the requested file is on another Tailscale peer, distinguish the three roles before acting: the user's laptop, the Hermes Mac Mini, and the target peer. Run `hostname`, `whoami`, and `pwd` after each SSH hop; only modify `~/.ssh/authorized_keys` after confirming the prompt is on the target host and target user. Tailscale reachability does not imply SSH availability: check the peer state, then probe TCP/SSH. On Arch-based targets the service is commonly `sshd.service`, not `ssh.service`; enable it interactively with `sudo systemctl enable --now sshd.service`, then verify `systemctl is-active sshd`.

For key-based access, generate or select the agent's key on the Hermes host, install only its public key on the target while the user is interactively logged in there, set `~/.ssh` to 700 and `authorized_keys` to 600, and test with `ssh -o BatchMode=yes`. Never request, record, or reuse a password in chat; if a password is accidentally disclosed, tell the user to rotate it immediately.

## Enable remote access (needs sudo → needs the user)
These require `sudo`, which the agent CANNOT do alone. Two paths:

**Path A — user approves interactively:** Re-run the sudo command; the Hermes app shows the user an approval prompt. Works only if the user is watching. Commands:
```bash
sudo systemsetup -setremotelogin on        # SSH
sudo defaults write /var/db/launchd.db/com.apple.launchd DisableRemoteAXInteraction -bool false  # AX
# Screen Sharing: enable in System Settings → Sharing → Screen Sharing
```

**Path B — user does it on the Mac (fastest, no sudo dance):** Tell them: *Ajustes → Compartir → Acceso remoto* (SSH) and *Compartir pantalla* (Screen Sharing). 2 minutes.

## Pitfalls
- Don't `brew install tailscale` expecting a PATH `tailscale` — use the bundle path above.
- Tailscale gives the NETWORK only. SSH/Screen Sharing are separate macOS services you still have to turn on.
- After `brew install --cask tailscale`, the FIRST launch needs a "Allow" click in System Settings → Privacy & Security for the network extension. Until then the daemon runs but no tunnel forms.
- Never write the sudo or SSH password into chat or `.env` — the sandbox blocks password piping, and credentials exposed in chat must be rotated immediately. Treat privileged setup and password authentication as requiring live user consent.
- After a user reports running a command through nested SSH, re-probe with a key-based, noninteractive command and do not assume the command ran on the intended host; host/user/path verification is the guard against editing the laptop or Mac instead of the target.

## Verify
- `pgrep -l Tailscale` → app process running.
- `/Applications/Tailscale.app/Contents/MacOS/tailscale status` → peers + online state.
- `sudo systemsetup -getremotelogin` → Remote Login: On (after SSH enabled).
