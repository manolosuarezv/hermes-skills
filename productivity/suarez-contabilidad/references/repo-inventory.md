# Inventario del repo contable Suárez (snapshot 22 AGO 2026)

Mapa rápido de qué script hace qué, para no re-auditar cada sesión.

## Pipeline VIVO (flujo real de registro)
- `agente_local_asientos.py` — parsea texto de WhatsApp con Ollama (qwen3:8b, $0) → borrador de asiento.
- `registrar_local.py` — escribe el movimiento en el xlsx local (100% local, SIN Drive). VIVO.
- `build_unificado.py` — regenera `contabilidad 2026.xlsx` (7 pestañas) + nota Obsidian. LEE solo, no toca orígenes. VIVO.
- `registrar_git.py` — commit git local + anota CHANGELOG. VIVO.
- `backup_qbex.py` — respalda a qbex (RAID vía SSH). VIVO.
- `cierre_diario.py` — orquestador: digest del día + backup. Pensado para cron (NO programado hoy).
- `~/bin/backup_contabilidad_diario.sh` — WOL a qbex, espera, corre backup_qbex, confirma, apaga. NO en cron.
- `~/bin/prender-server.py` — Wake-on-LAN a qbex (magic packet a las 2 NIC).

## Auxiliares / control
- `digest_diario.py` — resumen de cambios del día desde `logs/contabilidad.log.jsonl`.
- `informe_semanal.py` — informe semanal (familia/Renata).
- `cola_claude.py` — cola de tareas para Claude.
- `control_creditos.py` — ventana/umbral de créditos para frenar gasto de API paga.

## Reparación puntual (ya cumplieron su trabajo → mover a `_archive/fixes/`)
- `borrar_pagos_luz.py`, `borrar_pruebas_enero.py`, `corregir_dup_nomina.py`, `fix_agosto.py` — parches quirúrgicos aplicados.

## MUERTOS / obsoletos (token Drive revocado → archivar)
- `registrar.py` (versión Drive), `subir_drive.py`, `reauth_drive.py` — dependen de `drive_token.json` revocado. `registrar_local.py` es el vivo.
- `_lee_trii.py` (17 líneas) — helper huérfano, nadie lo importa.

## Vistas HTML
- `gen_vista.py` → `vista_portafolio_trii.html`
- `gen_vista_completa.py` → `vista_contabilidad_2026.html`
- Solapamiento alto con `build_unificado.py` (que ya da xlsx + Obsidian).

## Redundancia crítica: lógica Trii
Tres implementaciones de las mismas reglas de agregación por ticker:
1. `calc_trii.py` (170 líneas) — fuente canónica pretendida.
2. `build_unificado.py:127` `leer_trii_portafolio()` — REESCRIBE la lógica, no importa calc_trii → riesgo de divergencia.
3. `gen_vista*.py` — reimplementan el resumen.
FIX pendiente: crear `scripts/trii_calc.py` (módulo único) e importarlo desde los demás.

## Estado de automatización
- `crontab -l` del usuario = VACÍO. launchd solo corre `ai.hermes.gateway`.
- → El respaldo diario no corre solo. Hay que programar `cierre_diario.py` (cron Hermes o plist launchd, ej. 23:30).
- WOL no despierta qbex desde S5 frío (solo desde suspendido S3) → el paso "prender" del backup falla hasta encendido manual.

## Basura acumulada
- 29 archivos `.bak`/`.backup_*` (651 KB) + 21 `.xlsx` en `_archive/`. `.gitignore` ya excluye `.bak`, así que solo ensucian el dir local.
- Retener solo los 2 `.backup_` más recientes en raíz; podar >30 días.
