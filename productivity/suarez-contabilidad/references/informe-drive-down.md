# Generar el informe semanal cuando Drive / el entorno del cron fallan

## 1. Invocación con entorno saneado (OBLIGATORIO desde cron/gateway)
El entorno de Hermes exporta `PYTHONPATH` apuntando al venv 3.11 de hermes-agent.
Cualquier script de contabilidad que importe `registrar` / `google.oauth2` (p.ej.
`informe_semanal.py`, `backup_qbex.py`, `digest_diario.py`, `cierre_diario.py`)
carga `cryptography` del build 3.11 bajo el py3.9 del venv del proyecto →
`ImportError: dlopen(...cryptography..._rust.abi3.so): symbol not found in flat namespace '_PyType_GetName'`.
Corre SIEMPRE con entorno limpio:

    cd /Users/manuelsuarez/.hermes/contabilidad
    env -u PYTHONPATH ./venv/bin/python3 scripts/informe_semanal.py familia --no-enviar
    # forma más agresiva que también funciona (usa solo el site-packages del venv):
    env -i HOME=$HOME PATH=/usr/bin:/bin ./venv/bin/python3 scripts/informe_semanal.py familia --no-enviar

(El `plist` de `cierre_diario.py` ya anula `PYTHONPATH` en `EnvironmentVariables`; ver `references/launchd-cierre.md`.)

## 2. Drive token revocado / inválido — dos firmas distintas
- `invalid_grant: Token has been expired or revoked` → el refresh_token fue revocado; re-OAuth manual.
- `invalid_client: The provided client secret is invalid` → el `client_secret` en `drive_token.json`
  NO coincide con el `client_id` en Google Cloud (el secreto del OAuth client fue rotado/regenerado,
  o el token fue generado contra otro client). El fix es re-crear la credencial OAuth (o pegar el
  nuevo `client_secret`) y re-OAuth. En AMBOS casos el xlsx LOCAL queda al día; solo falla el push a Drive.
  Ninguno es automatizable desde cron → reporta el fallo exacto.

## 3. Shim para `informe_semanal.py` cuando Drive no responde
`informe_semanal.py` NO tiene contraparte `_local` (a diferencia de `registrar.py` / `registrar_local.py`).
Si solo necesitas el TEXTO del informe (p.ej. el correo dominical "¿quieres el informe?") y Drive está
caído, monkeypatchea `registrar.descargar` / `registrar.subir` para usar el xlsx local + el link cacheado.
Así usas la lógica real de `generar_informe()` sin tocar los scripts del usuario:

    # scripts/generar_informe_local.py
    import sys, os
    BASE = "/Users/manuelsuarez/.hermes/contabilidad"
    sys.path.insert(0, os.path.join(BASE, "scripts"))
    import registrar as R
    FAM = os.path.join(BASE, "contabilidad familia suarez 2026.xlsx")
    CACHED_LINK = "https://docs.google.com/spreadsheets/d/FILE_ID_UNIFICADA/edit?usp=drivesdk&ouid=TU_GOOGLE_OUID&rtpof=true&sd=true"
    R.descargar = lambda key: FAM          # archivo local, no Drive
    R.subir = lambda key: CACHED_LINK      # link cacheado, no sube
    import informe_semanal as I
    texto, link = I.generar_informe("familia")
    print(texto); print("LINK_DRIVE=" + link)

Correr con el entorno saneado del punto 1.

## 4. ⚠️ Discrepancia del link de "archivo familia"
El link en `drive_links.txt` (`.../d/FILE_ID_UNIFICADA/...`) es el de la hoja de cálculo
UNIFICADA `contabilidad 2026.xlsx` subida el 19-ago (según LOG_TRAZABILIDAD.md), **NO** el de
`contabilidad familia suarez 2026.xlsx`. El file id de ESTE último (según el SKILL.md) es
`FILE_ID_FAMILIA`.
→ Si una tarea pide "el link del archivo familia", el link cacheado puede ser el INCORRECTO.
  Verifica contra el file id de familia (o usa `files().get(fileId=FILE_ID_FAMILIA, fields=webViewLink)`
  tras re-autenticar) antes de enviarlo. No asumas que `drive_links.txt` = familia.

## 5. Correo dominical "¿quieres el informe?" (pregunta, NO el informe completo)
Asunto: `Pregunta informe dominical contabilidad`
Cuerpo:
    Hola Manolo, hoy es domingo. ¿Quieres que te envie el informe semanal de la contabilidad de la familia Suarez? Responde SI y te lo mando al instante. Link al Drive: <link familia>
Destinatario: USUARIO_GITHUB@gmail.com — desde: hermenegildo-hermes@DOMINIO_AGENTMAIL.
NO enviar el informe completo hasta que el usuario confirme "SI".
Si el envío falla (AgentMail MCP 403 / sin msmtp), entrega la pregunta + link vía el reporte propio del
cron y provee el contenido listo-para-enviar; no marques el informe como "enviado".
