# Reauth de Drive por consola — fix Error 400 redirect_uri

## Síntoma
Al abrir la URL de autorización generada por `reauth_drive.py`, Google muestra:
`Error 400: invalid_request — Missing required parameter: redirect_uri`

## Causa
El script usaba el redirect URI `urn:ietf:wg:oauth:2.0:oob` (flujo
"out-of-band"). Google lo **deshabilitó** para clientes de escritorio (desde
~2022). Sin un `redirect_uri` válido, la auth URL está mal formada y la
consola de Google la rechaza.

## Fix
Usar `redirect_uri=http://localhost:PORT/` y `InstalledAppFlow`
(google-auth-oauthlib). El puerto localhost no requiere verificación de
dominio para clientes tipo "Desktop app".

```python
import json
from google_auth_oauthlib.flow import InstalledAppFlow

d = json.load(open('drive_token.json'))
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
print("ABRE_ESTA_URL:", auth_url)
# Usuario abre en navegador, da Permitir. Google redirige a
# http://localhost:8088/?code=4/0A...&scope=... (la pagina no carga, es normal).
# Copiar el texto que aparece TRAS 'code=' en la barra de direcciones.
raw = input("PEGAME_EL_CODE: ").strip()
if "code=" in raw:
    from urllib.parse import urlparse, parse_qs
    raw = parse_qs(urlparse(raw).query).get('code', [raw])[0]
flow.fetch_token(code=raw)
creds = flow.credentials
new = {
    'token': creds.token,
    'refresh_token': creds.refresh_token or d.get('refresh_token'),
    'token_uri': creds.token_uri,
    'client_id': creds.client_id,
    'client_secret': creds.client_secret,
    'scopes': list(creds.scopes),
    'universe_domain': getattr(creds, 'universe_domain', 'googleapis.com'),
    'account': d.get('account'),
    'expiry': creds.expiry.isoformat() if creds.expiry else None,
}
json.dump(new, open('drive_token.json', 'w'), indent=2)
print("TOKEN_RENOVADO_OK")
```

## Notas
- El `redirect_uri` debe coincidir con uno declarado en el cliente OAuth de
  Google Cloud (tipo "Desktop app" permite `http://localhost`).
- Es INDEPENDIENTE del setup de `google-workspace` (ese usa su propio
  `setup.py` con PKCE y puerto efímero). Aquí es un reauth manual del token
  ya existente en `drive_token.json` (cuando da `invalid_grant`).
- Tras renovar, sube los xlsx con:
  `files().update(fileId=fid, media_body=MediaFileUpload(path, resumable=True))`.
- Si el navegador del usuario es el Mac mini headless, el agente imprime la
  URL y el usuario la abre en SU navegador (cualquier máquina), luego pega el
  code en el canal. No hace falta navegador en el server.
