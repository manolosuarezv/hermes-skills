#!/usr/bin/env bash
# Backup de la biblioteca de skills de Hermes a multiples destinos.
#
# Uso:
#   backup-skills.sh                  # los 3 destinos
#   backup-skills.sh git usb          # subconjunto
#
# Env (ajustar):
#   HERMES_HOME   default ~/.hermes
#   USB_MOUNT     default /Volumes/Tritones
#   USB_LABEL     default TritonEs
#   QBEX_HOST     default 192.168.1.69
#   QBEX_USER     default user01
#   QBEX_REMOTE   default /mnt/raid/backups/hermes
#   GH_REPO       default <owner>/hermes-skills

set -uo pipefail

HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
SKILLS_DIR="$HERMES_HOME/skills"
USB_MOUNT="${USB_MOUNT:-/Volumes/Tritones}"
USB_LABEL="${USB_LABEL:-Tritones}"
QBEX_HOST="${QBEX_HOST:-192.168.1.69}"
QBEX_USER="${QBEX_USER:-user01}"
QBEX_REMOTE="${QBEX_REMOTE:-/mnt/raid/backups/hermes}"
GH_REPO="${GH_REPO:-}"

TS="$(date +%Y%m%d_%H%M%S)"
STAGE="/tmp/skills-stage-$TS"
LOCAL_TGZ="/tmp/skills-$TS.tar.gz"

EXCLUDES=(
  --exclude='.git' --exclude='.archive' --exclude='.hub'
  --exclude='.curator_*' --exclude='.usage.json*'
  --exclude='__pycache__' --exclude='*.pyc' --exclude='.venv'
  --exclude='._*'
)

WANTED=("${@:-git usb remote}")
has() { [[ " ${WANTED[*]} " == *" $1 "* ]]; }

fail=0
note() { printf '%-8s %s\n' "$1" "$2"; }

# ---------------------------------------------------------------- git local
if has git; then
  if [[ -d "$SKILLS_DIR/.git" ]]; then
    if git -C "$SKILLS_DIR" diff --quiet HEAD 2>/dev/null; then
      note GIT "sin cambios desde el ultimo commit"
    else
      git -C "$SKILLS_DIR" add -A
      git -C "$SKILLS_DIR" commit -q -m "backup: skills $(date +%F)" \
        && note GIT "commit $(git -C "$SKILLS_DIR" rev-parse --short HEAD)"
    fi
  else
    git -C "$SKILLS_DIR" init -q
    git -C "$SKILLS_DIR" add -A
    git -C "$SKILLS_DIR" commit -q -m "initial: snapshot de skills"
    note GIT "repo inicializado"
  fi
fi

# ---------------------------------------------------------------- staging
rm -rf "$STAGE"
mkdir -p "$STAGE"
if rsync -a "${EXCLUDES[@]}" "$SKILLS_DIR/" "$STAGE/"; then
  find "$STAGE" -name '._*' -delete
  tar -czf "$LOCAL_TGZ" -C "$STAGE" .
  note STAGE "$(du -h "$LOCAL_TGZ" | cut -f1) staged"
else
  note STAGE "FALLO rsync al staging"
  fail=1
fi

# ---------------------------------------------------------------- disco USB
if has usb; then
  DEST="$USB_MOUNT/backups/hermes/skills"
  if mountpoint -q "$USB_MOUNT" 2>/dev/null || [[ -d "$USB_MOUNT" ]]; then
    mkdir -p "$DEST"
    cp "$LOCAL_TGZ" "$DEST/" 2>/dev/null
    for f in MANIFEST.json CHANGELOG.txt README.md; do
      [[ -f "$STAGE/$f" ]] && cp "$STAGE/$f" "$DEST/" 2>/dev/null
    done
    find "$DEST" -name '._*' -delete 2>/dev/null
    SRC_H="$(shasum -a 256 "$LOCAL_TGZ" | cut -d' ' -f1)"
    DST_H="$(shasum -a 256 "$DEST/$(basename "$LOCAL_TGZ")" 2>/dev/null | cut -d' ' -f1)"
    [[ "$SRC_H" == "$DST_H" ]] && note USB "OK $(basename "$LOCAL_TGZ") checksum coincide" \
                              || { note USB "FALLO checksum"; fail=1; }
  else
    note USB "NO MONTADO ($USB_LABEL en $USB_MOUNT)"
    fail=1
  fi
fi

# ---------------------------------------------------------------- remoto (WOL -> rsync)
if has remote; then
  if ping -c1 -W2 "$QBEX_HOST" >/dev/null 2>&1; then
    note REMOTO "$QBEX_HOST responde"
    ssh -o BatchMode=yes -o ConnectTimeout=8 "$QBEX_USER@$QBEX_HOST" \
      "mkdir -p '$QBEX_REMOTE/skills/$TS'" >/dev/null 2>&1
    if scp -o BatchMode=yes -q -r "$LOCAL_TGZ" \
         "$QBEX_USER@$QBEX_HOST:$QBEX_REMOTE/skills/$TS/" 2>/dev/null; then
      ssh -o BatchMode=yes -o ConnectTimeout=8 "$QBEX_USER@$QBEX_HOST" \
        "ls -la '$QBEX_REMOTE/skills/$TS'" >/dev/null 2>&1 \
        && note REMOTO "OK copiado y verificado" \
        || { note REMOTO "copiado pero NO verificado"; fail=1; }
    else
      note REMOTO "FALLO scp"
      fail=1
    fi
  else
    note REMOTO "$QBEX_HOST apagado"
    note "" "WOL: ~/bin/prender-server.py && poll --check hasta 120s"
    fail=1
  fi
fi

# ---------------------------------------------------------------- github (manual por defecto)
if has github; then
  if [[ -z "$GH_REPO" ]]; then
    note GITHUB "GH_REPO vacio — push manual (ver references/github-publish.md)"
  else
    tmp="/tmp/skills-push-$TS"
    git clone -q "https://github.com/$GH_REPO.git" "$tmp" 2>/dev/null
    if [[ -d "$tmp" ]]; then
      rsync -a --delete "${EXCLUDES[@]}" --exclude='.git' "$STAGE/" "$tmp/"
      git -C "$tmp" add -A
      git -C "$tmp" commit -q -m "backup: $(date +%F)" 2>/dev/null \
        && git -C "$tmp" push -q origin HEAD:main \
        && note GITHUB "OK $GH_REPO" \
        || note GITHUB "sin cambios o push fallo"
      rm -rf "$tmp"
    else
      note GITHUB "FALLO clone"
      fail=1
    fi
  fi
fi

rm -rf "$STAGE"
[[ $fail -eq 0 ]] && note RESULT "OK" || note RESULT "HAY FALLOS — revisar arriba"
exit $fail