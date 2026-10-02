#!/usr/bin/env bash
# prender-server-mac.sh — macOS port of prender-server v5.1 (bash orchestrator)
# Wakes qbex (server01) from the Mac mini.
#   HOME  : WOL broadcast local -> ping -> auto-SSH with key.
#   REMOTE: mosquitto_pub MQTT -> ESP32 relay sends the magic packet.
# Secrets MUST come from the environment (do NOT hardcode WiFi/MQTT creds).
# macOS fixes vs the Linux original are marked [macOS].
# Verified 2026-08-17 on the Mac mini: cold-boot WOL qbex in ~50s + auto-SSH OK.

set -u
HOST_LOCAL="${HOST_LOCAL:-192.168.1.69}"
HOST_TAILSCALE="${HOST_TAILSCALE:-100.119.118.124}"
USER_NAME="${USER_NAME:-user01}"
MAC1="${MAC1:-44:87:fc:ea:69:da}"   # qbex enp0s7 (100M, slow)
MAC2="${MAC2:-1c:86:0b:2d:e2:c8}"   # qbex enp4s0 (1G, fast)
BROADCAST_LOCAL="${BROADCAST_LOCAL:-192.168.1.255}"
HOME_SUBNET="${HOME_SUBNET:-192.168.1}"
MQTT_HOST="${MQTT_HOST:-broker.example.com}"
MQTT_PORT="${MQTT_PORT:-8883}"
MQTT_USER="${MQTT_USER:-esp32wol}"
MQTT_PASSWORD="${MQTT_PASSWORD:-}"  # REQUIRED from env
MQTT_TOPIC="${MQTT_TOPIC:-home/wol}"
SSH_PORT="${SSH_PORT:-22}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/id_ed25519_qbex}"
PING_TRIES="${PING_TRIES:-3}"
PING_WAIT="${PING_WAIT:-15}"
MAX_CYCLES="${MAX_CYCLES:-10}"
GLOBAL_TIMEOUT="${GLOBAL_TIMEOUT:-480}"
LOGFILE="${LOGFILE:-$HOME/prender-server.log}"

R='\033[0;31m'; G='\033[0;32m'; Y='\033[1;33m'; C='\033[0;36m'; B='\033[1m'; X='\033[0m'

log(){ local lvl="$1"; shift
  local col="$X"; case "$lvl" in ERR)col="$R";;OK)col="$G";;WARN)col="$Y";;INFO)col="$C";;esac
  printf "${col}[$(date '+%Y-%m-%d %H:%M:%S')] $*${X}\n" | tee -a "$LOGFILE"
}

check_deps(){
  command -v wakeonlan >/dev/null 2>&1 || { log ERR "wakeonlan no instalado: brew install wakeonlan"; exit 1; }
  command -v mosquitto_pub >/dev/null 2>&1 || { log ERR "mosquitto_pub no instalado: brew install mosquitto"; exit 1; }
  [ -f "$SSH_KEY" ] || { log ERR "llave SSH no encontrada: $SSH_KEY"; exit 1; }
  [ -n "$MQTT_PASSWORD" ] || log WARN "MQTT_PASSWORD vacio (solo necesario en modo remoto)"
}

# [macOS] route -n get has NO 'source:' line on macOS; get IP from the egress iface.
detect_location(){
  local src_ip="" iface
  iface=$(route -n get 8.8.8.8 2>/dev/null | awk '/interface:/{print $2}')
  [ -n "$iface" ] && src_ip=$(ipconfig getifaddr "$iface" 2>/dev/null)
  [ -z "$src_ip" ] && src_ip=$(ifconfig 2>/dev/null | awk '/inet / && $2!="127.0.0.1"{print $2; exit}')
  # [macOS] log to stderr so the captured $(...) value stays clean for the if-test
  log INFO "IP de salida: ${src_ip:-desconocida} (iface ${iface:-?})" >&2
  if [[ "$src_ip" == "${HOME_SUBNET}."* ]]; then echo "home"; else echo "remote"; fi
}

send_wol_local(){
  log INFO "Magic packet via red local (broadcast $BROADCAST_LOCAL)..."
  wakeonlan -i "$BROADCAST_LOCAL" "$MAC1" >/dev/null 2>&1 && log OK "  MAC1 enp0s7  ($MAC1)" || log ERR "  MAC1 fallo"
  wakeonlan -i "$BROADCAST_LOCAL" "$MAC2" >/dev/null 2>&1 && log OK "  MAC2 enp4s0 ($MAC2)" || log ERR "  MAC2 fallo"
}

# [macOS] /etc/ssl/certs does not exist; use brew openssl path if present.
send_wol_mqtt(){
  log INFO "WOL via MQTT -> ESP32 relay..."
  local capath="/etc/ssl/certs"
  [ -d /opt/homebrew/etc/openssl@3/certs ] && capath="/opt/homebrew/etc/openssl@3/certs"
  if mosquitto_pub -h "$MQTT_HOST" -p "$MQTT_PORT" --capath "$capath" \
        -u "$MQTT_USER" -P "$MQTT_PASSWORD" -t "$MQTT_TOPIC" -m "wake" 2>&1 | tee -a "$LOGFILE"; then
    log OK "Mensaje MQTT enviado -> ESP32 enviara magic packet"
  else
    log ERR "Error enviando mensaje MQTT"
  fi
}

# [macOS] no 'timeout' command; use BSD nc -w (total) and -G (connect) timeouts.
check_ssh(){ nc -z -w 3 -G 3 "$1" "$SSH_PORT" >/dev/null 2>&1; }
check_ping(){ ping -c 1 -t 2 "$1" >/dev/null 2>&1; }

# [macOS] tailscale usually not installed; detect + skip instead of hard-fail.
disable_tailscale_dns(){ command -v tailscale >/dev/null 2>&1 && sudo tailscale set --accept-dns=false || log INFO "tailscale no instalado en Mac; salto DNS"; }
restore_tailscale_dns(){ command -v tailscale >/dev/null 2>&1 && sudo tailscale set --accept-dns=true || true; }

start_ts=$(date +%s.%N)
printf "${B}=== prender-server [Darwin] ===${X}\n"
check_deps
LOCATION=$(detect_location)
log INFO "Ubicacion: $LOCATION"

if [ "$LOCATION" = "home" ]; then
  HOST="$HOST_LOCAL"; TARGET_DESC="LAN local"
else
  HOST="$HOST_TAILSCALE"; TARGET_DESC="Tailscale"
  disable_tailscale_dns
  send_wol_mqtt
fi

for cycle in $(seq 1 "$MAX_CYCLES"); do
  elapsed=$(awk "BEGIN{printf \"%.1f\", $(date +%s.%N)-$start_ts}")
  [ "$(awk "BEGIN{print ($elapsed>=$GLOBAL_TIMEOUT)?1:0}")" = "1" ] && { log ERR "Timeout global $GLOBAL_TIMEOUT s alcanzado"; break; }
  for try in $(seq 1 "$PING_TRIES"); do
    if ! check_ping "$HOST"; then
      log INFO "Ciclo $cycle/$MAX_CYCLES — Intento $try/$PING_TRIES: $TARGET_DESC sin respuesta, enviando WOL..."
      [ "$LOCATION" = "home" ] && send_wol_local || send_wol_mqtt
      sleep "$PING_WAIT"; continue
    fi
    log INFO "Ping OK a $HOST"
    if check_ssh "$HOST"; then
      log OK "Puerto $SSH_PORT abierto. Conectando a ${USER_NAME}@${HOST}..."
      printf "${B}===============================================================${X}\n"
      ssh -i "$SSH_KEY" -o StrictHostKeyChecking=accept-new "${USER_NAME}@${HOST}"
      printf "${B}===============================================================${X}\n"
      log OK "Sesion finalizada. Tiempo total: $(awk "BEGIN{printf \"%.1f\", $(date +%s.%N)-$start_ts}")s"
      [ "$LOCATION" = "remote" ] && restore_tailscale_dns
      exit 0
    fi
    log INFO "Ping OK pero SSH aun no responde..."
    sleep "$PING_WAIT"
  done
  [ "$LOCATION" = "home" ] && send_wol_local || send_wol_mqtt
done

log ERR "No fue posible despertar/conectar al servidor tras $(awk "BEGIN{printf \"%.1f\", $(date +%s.%N)-$start_ts}")s."
[ "$LOCATION" = "remote" ] && restore_tailscale_dns
exit 1
