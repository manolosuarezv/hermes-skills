#!/usr/bin/env bash
# guardar_raid.sh — Copia un archivo al RAID de qbex (server01) con el flujo
#   WOL -> esperar encendido -> montar RAID -> mkdir -> scp -> verificar -> apagar.
#
# Cubre la peticion recurrente "guarda X en el raid" (documentos sueltos: RUT,
# declaraciones de renta, contratos, etc.) que NO es el backup diario de xlsx.
#
# Uso:
#   bash guardar_raid.sh <origen_local> <subdir_bajo_/mnt/raid> [nombre_destino] [--no-poweroff]
#
#   origen_local : ruta del archivo en el Mac (un solo archivo por llamada).
#   subdir_bajo_/mnt/raid : p.ej. "documentos/rut" o "documentos/declaraciones/2025".
#   nombre_destino : opcional; por defecto usa el basename del origen.
#                    Usarlo para renombrar al copiar (p.ej. "Rut 2026 actualizado.pdf").
#   --no-poweroff : NO apaga qbex al final (para encadenar varias copias seguidas).
#
# Requisitos (ya verificados en el homelab):
#   - prender-server.py en la misma carpeta (hace el WOL a ambas NIC).
#   - SSH key /Users/manuelsuarez/.ssh/id_ed25519_qbex, usuario user01, NOPASSWD sudo.
#   - RAID1 en /mnt/raid (se monta si no esta montado).
#
# Convenciones de carpetas en el RAID (mantenerlas):
#   /mnt/raid/documentos/rut/                  -> RUT / cedula / docs de identidad
#   /mnt/raid/documentos/declaraciones/<AÑO>/  -> declaraciones de renta
#   /mnt/raid/backups/contabilidad_suarez/     -> xlsx (ver backup-schedule.md)
set -e

IP=192.168.1.69
KEY=/Users/manuelsuarez/.ssh/id_ed25519_qbex
USER=user01
HERE="$(cd "$(dirname "$0")" && pwd)"
POWEROFF=1

args=()
while [ $# -gt 0 ]; do
  case "$1" in
    --no-poweroff) POWEROFF=0; shift;;
    *) args+=("$1"); shift;;
  esac
done

SRC="${args[0]}"
SUB="${args[1]}"
DST_NAME="${args[2]:-$(basename "$SRC")}"

[ -n "$SRC" ] || { echo "USO: guardar_raid.sh <origen> <subdir_raid> [nombre_destino] [--no-poweroff]"; exit 2; }
[ -f "$SRC" ] || { echo "ERROR: origen no existe: $SRC"; exit 2; }
[ -n "$SUB" ] || { echo "ERROR: falta el subdirectorio bajo /mnt/raid"; exit 2; }

DST_DIR="/mnt/raid/$SUB"
DST_PATH="$DST_DIR/$DST_NAME"
SSH="ssh -i $KEY -o BatchMode=yes -o StrictHostKeyChecking=no ${USER}@${IP}"

echo "[1] WOL -> qbex (ambas NIC)"; python3 "$HERE/prender-server.py"

echo "[2] esperando encendido (hasta ~80s)..."; up=0
for i in $(seq 1 20); do
  if ping -c1 -t3 "$IP" >/dev/null 2>&1; then echo "  UP (~$((i*4))s)"; up=1; break; fi
  sleep 4
done
[ $up -eq 0 ] && { echo "ERROR: qbex no encendio"; exit 2; }

echo "[3] montando RAID + mkdir $DST_DIR"
$SSH "test -d /mnt/raid || sudo mount /mnt/raid; mkdir -p '$DST_DIR'"

echo "[4] scp: $SRC -> $DST_PATH"
scp -i "$KEY" -o BatchMode=yes -o StrictHostKeyChecking=no "$SRC" "${USER}@${IP}:${DST_PATH}"

echo "[5] verificando en RAID"
$SSH "ls -la '$DST_DIR' && test -f '$DST_PATH' && echo COPIA_OK"

if [ $POWEROFF -eq 1 ]; then
  echo "[6] apagando qbex (systemctl poweroff -f)"
  $SSH 'sudo systemctl poweroff -f'
  echo "    esperando bajada RAID (~80s)..."; sleep 80
  off=0
  for s in $(seq 1 15); do
    if ping -c1 -t3 "$IP" >/dev/null 2>&1; then sleep 8; else echo "qbex OFF"; off=1; break; fi
  done
  [ $off -eq 0 ] && echo "qbex AUN ON -- verificar manualmente" || echo "RESULTADO: qbex OFF"
else
  echo "RESULTADO: copia OK, qbex queda ENCENDIDO (--no-poweroff)"
fi
