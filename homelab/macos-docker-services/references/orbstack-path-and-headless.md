# OrbStack on macOS — PATH quirk & headless launch

## The PATH problem (costs you a failed first `docker` call every time)
After `brew install --cask orbstack`, `docker` is NOT on the normal brew bin path.
It lands in the user's home, symlinked by OrbStack:

  ~/.orbstack/bin/docker            -> /Applications/OrbStack.app/Contents/MacOS/xbin/docker
  ~/.orbstack/bin/docker-compose    -> .../xbin/docker-compose
  ~/.orbstack/bin/orb               -> .../bin/orb
  ~/.orbstack/bin/orbctl            -> .../bin/orbctl

So `which docker` fails and `/opt/homebrew/bin/docker` does not exist.
The agent command shell does NOT load the login profile, so even though the
user's interactive terminal might find it, the agent's shell won't.

FIX (prepend in every docker command):
  export PATH="$HOME/.orbstack/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

Verify once:
  orbctl status        # -> Running
  docker --version     # e.g. Docker version 29.4.0
  docker compose version

## Headless launch
OrbStack needs to boot its VM once after install. From the agent shell:
  open -a OrbStack     # launches the app, boots the Linux VM in background
  sleep 12
  orbctl status        # Running

No GUI interaction required — `open -a` is enough on a headless Mac Mini that
already has a desktop session. If there is no user session at all, OrbStack
won't auto-boot; a user must log in once or run `orbctl start`.

## Command-guard pitfall
The agent terminal guard may refuse `docker compose up -d` as "long-lived
server/watch process" even though `-d` detaches and returns. Run it with
`background=true` and then poll, OR the guard will hard-block it. It's a false
positive — `up -d` exits immediately.
