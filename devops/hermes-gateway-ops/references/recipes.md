# Recipes & exact strings

## Check gateway status
```
launchctl list | grep hermes.gateway
# 952  0   ai.hermes.gateway   -> running, exit 0 recently
tail -5 ~/.hermes/logs/gateway.log
```

## Check Tailscale (CLI not on PATH after cask install)
```
/Applications/Tailscale.app/Contents/MacOS/tailscale status
# 100.101.1.51  HOSTNAME_MAC  <USUARIO_GITHUB>@  macOS  -
```
No utun/tun process = network extension not yet approved in System Settings.

## Sandbox block strings (do NOT retry blindly)
- Stop/restart gateway from inside: "cannot restart or stop the gateway from inside the gateway process... Run `hermes gateway restart` from a separate shell outside the running gateway."
- sudo -S: "BLOCKED: sudo password guessing via stdin (sudo -S). Do not pipe passwords to 'sudo -S'..."
- sudo needs approval: command times out "without user response. The user has NOT consented to this action."

## Always-false assumption check for unknown hosts
```
ps aux | grep -i NAME | grep -v grep
ls -d ~/*NAME* /usr/local/*NAME* /opt/*NAME*
grep -i NAME /etc/hosts
launchctl list | grep -i NAME
```
