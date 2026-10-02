# Drive token troubleshooting (backup_qbex.py / registrar.py)

## Síntoma
El backup diario falla así (en `backup_qbex.py`, paso `descargar()` → `files().list`):

```
google.auth.exceptions.RefreshError: ('invalid_grant: Token has been expired or revoked.',
  {'error': 'invalid_grant', 'error_description': 'Token has been expired or revoked.'})
FALLO backup
RESPALDO_CONFIRMADO
```

## Trampa importante: RESPALDO_CONFIRMADO NO es un backup
El wrapper `backup_contabilidad_diario.sh` hace la confirmación con un
`ssh ... 'test -f ... && echo RESPALDO_CONFIRMADO'`. Eso solo comprueba que los
archivos *anteriores* ya están en el RAID. Si el backup falló arriba, el
`RESPALDO_CONFIRMADO` es engañoso: confirma archivos viejos, NO un respaldo nuevo.
El reporte del cron DEBE distinguir "archivos viejos presentes" de "backup nuevo del día".

## Diagnóstico (headless, sin navegador)
```bash
cd /Users/manuelsuarez/.hermes/contabilidad
source venv/bin/activate
python3 -c "
from google.oauth2.credentials import Credentials
import json, google.auth.transport.requests as tr
d=json.load(open('drive_token.json'))
c=Credentials(token=d['token'], refresh_token=d.get('refresh_token'),
              token_uri=d['token_uri'], client_id=d['client_id'],
              client_secret=d['client_secret'], scopes=d['scopes'])
try:
    c.refresh(tr.Request()); print('REFRESH OK')
except Exception as e:
    print('REFRESH FALLÓ:', type(e).__name__, str(e)[:120])
"
```
- `REFRESH OK` → el token sirve; el fallo es otro.
- `REFRESH FALLÓ: RefreshError ... invalid_grant ...` → el refresh_token fue
  revocado/expirado. Es el caso típico.

También revisar `ls -la drive_token.json`: si la fecha de modificación tiene
~7+ días y la app OAuth está en modo "testing", es la causa.

## Causa raíz más común
La app de Google Cloud OAuth está en **modo "testing"** → Google revoca los
refresh tokens automáticamente a los **7 días**. Por eso el backup falla cada
noche tras esa ventana, aunque el archivo `drive_token.json` siga presente.

## Fix (requiere acción del usuario — NO es autónomo)
1. **Mover la app a "production"** en Google Cloud Console → APIs & Services →
   OAuth consent screen → Publishing status → "PUBLISH". Así los refresh tokens
   no caducan a los 7 días. (Esto previene recurrencia.)
2. **Regenerar el token** re-ejecutando el flujo de autorización OAuth que creó
   `drive_token.json` (necesita navegador + consentimiento del usuario; no se
   puede hacer headless ni desde un cron).
3. Verificar con el diagnóstico de arriba (`REFRESH OK`) y volver a correr
   `backup_contabilidad_diario.sh`.

Hasta no arreglarlo, el backup diario falla todas las noches con el mismo error.

## Otro error de OAuth: `Error 400: invalid_request — Missing required parameter: redirect_uri`
Síntoma: al abrir la URL de autorización que arma un script manual de re-auth,
Google muestra "Access blocked: Authorization Error … Error 400: invalid_request …
Missing required parameter: redirect_uri".

Causa: el script usaba `redirect_uris: ["urn:ietf:wg:oauth:2.0:oob"]` (flujo
"out-of-band"). Google **deshabilitó el redirect `oob` para apps de escritorio**;
ahora exige un `redirect_uri` real. (Ojo: este es un error DISTINTO de
`invalid_grant`: `invalid_grant` = token revocado/expirado; `redirect_uri` =
la URL de auth está mal armada y ni siquiera deja llegar al consentimiento.)

Fix en el script (p.ej. `reauth_drive.py`): usar `http://localhost:PORT/` y
parsear el `code` desde la URL a la que Google redirige:

```python
client_config = {
    "installed": {
        "client_id": d['client_id'],
        "client_secret": d['client_secret'],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": d['token_uri'],
        "redirect_uris": ["http://localhost:8088/"]
    }
}
flow = InstalledAppFlow.from_client_config(client_config, scopes=d['scopes'])
flow.redirect_uri = "http://localhost:8088/"
auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
# enviar auth_url al usuario; tras Permitir, Google redirige a
# http://localhost:8088/?code=4/0A...&scope=... (la pagina no carga, es normal)
code = input("PEGAME_EL_CODE_AQUI: ").strip()
if "code=" in code:
    from urllib.parse import urlparse, parse_qs
    code = parse_qs(urlparse(code).query).get("code", [code])[0]
flow.fetch_token(code=code)
```

No uses `oob`. Tras el token, verificar con el diagnóstico de arriba (`REFRESH OK`).
