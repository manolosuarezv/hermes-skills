# launchd — cierre diario de contabilidad (22 AGO 2026, sesión 2)

## Objetivo
Programar `scripts/cierre_diario.py` (digest del día + backup a qbex) a las 23:30
todos los días, sin depender del scheduler de Hermes ni de un cron manual.

## Plist canónico (YA CREADO en la sesión 2)
Ruta: `/Users/manuelsuarez/Library/LaunchAgents/com.suarez.contabilidad.cierre.plist`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.suarez.contabilidad.cierre</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/manuelsuarez/.hermes/contabilidad/venv/bin/python3</string>
        <string>/Users/manuelsuarez/.hermes/contabilidad/scripts/cierre_diario.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/manuelsuarez/.hermes/contabilidad</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PYTHONPATH</key>
        <string></string>
        <key>PATH</key>
        <string>/Users/manuelsuarez/.hermes/contabilidad/venv/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>23</integer>
        <key>Minute</key>
        <integer>30</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/Users/manuelsuarez/.hermes/contabilidad/logs/cierre_diario.out.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/manuelsuarez/.hermes/contabilidad/logs/cierre_diario.err.log</string>
    <key>RunAtLoad</key>
    <false/>
    <key>AbandonProcessGroup</key>
    <true/>
</dict>
</plist>
```

## GOTCHA CRÍTICO — `PYTHONPATH=""` es OBLIGATORIO
El `EnvironmentVariables` con `PYTHONPATH` vacío NO es opcional. launchd hereda el
entorno del gateway de Hermes cuando el Mac arranca esa sesión; si `PYTHONPATH` apunta
al venv 3.11 del gateway, el venv 3.9 de contabilidad rompe `cryptography`
(`symbol not found` / `ImportError`) y el backup falla en silencio (el `.err.log` lo
muestra). `cierre_diario.py` ya hace `_clean_env()` que hace `e.pop("PYTHONPATH")`, pero
ponerlo también en el plist anula el valor en el arranque. `PATH` explícito garantiza
que `venv/bin` esté primero.

## Cargar / descargar
```bash
# crear carpeta de logs si no existe
mkdir -p /Users/manuelsuarez/.hermes/contabilidad/logs

# cargar (lo dispara a las 23:30 de cada día, sin correr al cargar por RunAtLoad=false)
launchctl load /Users/manuelsuarez/Library/LaunchAgents/com.suarez.contabilidad.cierre.plist

# verificar que está cargado
launchctl list | grep com.suarez.contabilidad.cierre

# descargar (si tocas el plist, descarga y vuelve a cargar)
launchctl unload /Users/manuelsuarez/Library/LaunchAgents/com.suarez.contabilidad.cierre.plist
```

## Gap conocido — WOL/S5 (no resuelto por el plist)
`cierre_diario.py` → `backup_qbex.py` asume que qbex está accesible. Si qbex está
APAGADO en S5 frío, el WOL de `prender-server.py` NO lo despierta (solo desde suspendido).
El plist NO soluciona eso. Mitigaciones (decisión de hardware/operativa, no de script):
- Dejar qbex en S3 (suspendido) en vez de `poweroff -f`, o
- Habilitar "WOL from S5" en BIOS, o
- Disparar el backup solo cuando qbex ya esté prendido (p.ej. desde el ThinkPad).

Hasta decidir eso, el cierre corre a las 23:30 pero el backup paso 2 fallará si qbex
está apagado (se verá en `logs/cierre_diario.err.log` / el digest reporta CIERRE_FAIL).

## Verificar el plist sin tocar producción
`PlistBuddy -c 'Print :Label' <plist>` confirma bien formado; `ET.parse()` en Python
también. El script `scripts/verify_trii.py` incluye un assert de las claves requeridas
(Label, ProgramArguments, StartCalendarInterval, EnvironmentVariables, StandardOutPath,
StandardErrorPath) y que el dir de StandardOutPath existe.
