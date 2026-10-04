# prender-server v5.1 — arquitectura y port a macOS

## Qué es (stack "madre")
Repo `<USUARIO_GITHUB>/prender-server` (privado). Contenido:
- `prender-server` — orquestador bash (v5.1): detecta ubicación (home/remote),
  envía WOL (broadcast local O vía MQTT→ESP32), espera, y abre SSH auto.
- `esp32_wol_relay.ino` — firmware ESP32: conecta a WiFi `Suarez2.4G`, se suscribe
  a MQTT (HiveMQ) topic `home/wol`, al recibir payload `wake` envía el magic packet
  a las 2 MACs de qbex; publica estado en `home/wol/status`.
- Detección home/remote:
  - HOME  → `wakeonlan -i 192.168.1.255 <MAC>` (broadcast LAN).
  - REMOTE → `mosquitto_pub` MQTT → ESP32 manda el WOL. Además
    `tailscale set --accept-dns=false` (Pi-hole apagado fuera de casa) y lo restaura al volver.
- Parámetros clave (qbex): HOST_LOCAL 192.168.1.69, HOST_TAILSCALE 100.119.118.124,
  USER user01, MAC1 44:87:fc:ea:69:da (enp0s7 100M), MAC2 1c:86:0b:2d:e2:c8 (enp4s0 1G),
  BROADCAST 192.168.1.255, MQTT host HiveMQ, topic home/wol, usuario esp32wol,
  PING_TRIES 3, PING_WAIT 15, MAX_CYCLES 10, GLOBAL_TIMEOUT 480, LOGFILE ~/prender-server.log.
- El script Python local de esta skill (`scripts/prender-server.py`) es SOLO un subconjunto
  mínimo: WOL LAN a las 2 MACs, sin MQTT/remoto/auto-SSH.

## Cómo instalar en la Mac mini (resumen 2026-08-17)
1. `brew install wakeonlan mosquitto` (mosquitto trae `mosquitto_pub`).
2. Copiar `scripts/prender-server-mac.sh` a `~/bin/prender-server`, `chmod +x`.
3. Secrets por env (NUNCA en claro en el script):
   `export MQTT_PASSWORD=***; export MQTT_HOST=***` antes de correr, o editar el header.
4. La llave SSH `id_ed25519_qbex` ya existe en `~/.ssh/`.

## 4 trampas GNU→BSD al portar el bash de Linux a macOS
1. **Detección de ubicación**: Linux `ip route get 8.8.8.8` imprime `src 192.168.1.x`;
   macOS `route -n get 8.8.8.8` NO tiene `source:` (usa `interface: en0`).
   → `iface=$(route -n get 8.8.8.8 | awk '/interface:/{print $2}'); src=$(ipconfig getifaddr "$iface")`.
   Sin esto, el script siempre cae en "remote" y nunca usa WOL local.
2. **Contaminación de captura**: si `detect_location` hace log a stdout Y `echo home/remote`,
   entonces `LOCATION=$(detect_location)` captura también el log y el `if [ "$LOCATION" = home ]`
   nunca matchea. → enviar el log a stderr (`log INFO "..." >&2`), dejar solo el echo en stdout.
3. **`timeout` es GNU-only**: macOS no tiene `timeout`. El `check_ssh` original
   `timeout 3 nc -z -w 2 host 22` FALLA siempre (comando no encontrado → non-zero),
   así que el script cree que SSH está caído aunque el puerto 22 esté abierto y loopea.
   → `nc -z -w 3 -G 3 "$host" "$SSH_PORT"` (`-w` timeout total, `-G` connect timeout).
4. **Certs MQTT**: Linux `/etc/ssl/certs/` no existe en macOS → `mosquitto_pub --capath`
   error. → usar `/opt/homebrew/etc/openssl@3/certs` si existe, si no omitir `--capath`.
   Además `tailscale` usualmente NO está en la Mac: detectar y saltar el paso DNS.

## Verificación real (2026-08-17, Mac mini)
- qbex OFF → `wakeonlan` a ambas MACs → encendió en ~50s (ping OK).
- SSH con llave `id_ed25519_qbex`: `CONECTADO_REAL / server01` exit 0.
- Script completo end-to-end (modo home, qbex ON): detecta home → WOL local →
  ping → puerto 22 → SSH real → exit 0.
- qbex apagado al final con `ssh ... 'sudo shutdown -h now'` (qbex tarda ~2 min en
  soltar ICMP; esperar ~75s antes de declarar OFF — ver SKILL.md "verify-off loop").

## No probado desde aquí
- Modo **remote** (fuera de casa): MQTT→ESP32. Cableado con certs brew, pero el
  broker HiveMQ no se alcanzó desde casa ("Protocol error"). Probar forzando
  `LOCATION=remote` o cuando la Mac esté fuera de la LAN.
- `tailscale set --accept-dns` (solo remoto y si se instala tailscale en la Mac).

## Seguridad
El repo original trae WiFi/MQTT en claro (en el .ino y el bash). NO hacer el repo
público sin mover creds a `secrets/.env`. En este port las creds vienen de env vars.
