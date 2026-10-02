# Correos bancarios → registro contable

Clase de tarea: leer el buzón del usuario, entender qué correo es un movimiento real, y registrarlo en la pestaña del producto que corresponda sin inventar filas ni montos.

## 1. Leer el buzón (solo lectura)

Credenciales: `~/.hermes/google_token.json` (token del usuario, válido). `drive_token.json` NO sirve para Gmail: es otro token y está inválido. El token del usuario trae scopes de Gmail, suficientes para leer y para etiquetar.

Ejecuta siempre con el venv del proyecto y sin heredar `PYTHONPATH`:

```bash
cd /Users/manuelsuarez/.hermes/contabilidad
env -u PYTHONPATH ./venv/bin/python3 /tmp/leer.py
```

```python
import base64, os, re, html
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

creds = Credentials.from_authorized_user_file(os.path.expanduser('~/.hermes/google_token.json'))
svc = build('gmail', 'v1', credentials=creds)
q = 'from:BANCO_DAVIVIENDA@davivienda.com OR from:nu@nu.com.co'
r = svc.users().messages().list(userId='me', q=q, maxResults=25, includeSpamTrash=True).execute()
m = svc.users().messages().get(userId='me', id=r['messages'][0]['id'], format='full').execute()

def cuerpo(msg):
    """texto plano del mensaje; los bancos mandan SOLO text/html"""
    def walk(p):
        if p.get('mimeType') == 'text/html' and p.get('body', {}).get('data'):
            h = base64.urlsafe_b64decode(p['body']['data']).decode('utf-8', 'replace')
            return html.unescape(re.sub(r'<[^>]+>', ' ', h))
        return ' '.join(filter(None, (walk(x) for x in p.get('parts', []))))
    return walk(msg['payload'])
```

Pitfall: `format='full'` + parsear `parts` recursivo. Los cuatro bancos mandan `text/html` únicamente, sin `text/plain`; buscar solo `text/plain` devuelve vacío y se pierde el movimiento. Normaliza espacios tras quitar etiquetas y usa `html.unescape`, porque los montos llegan como `&nbsp;` y `Compraste` en entidades.

Los extractos mensuales (Bancolombia) traen el detalle en PDF adjunto, no en el cuerpo: no los parsees a ciegas, van a la cola de pendientes.

## 2. Remitentes: whitelist exacta, nunca búsqueda por dominio

Solo estos remitentes son movimientos:

| Emisor | Remitente |
|---|---|
| Davivienda (crédito y débito) | `BANCO_DAVIVIENDA@davivienda.com` |
| Nu (tarjeta y cuenta) | `nu@nu.com.co` |
| Nequi | `notificaciones@nequi.com.co` |
| Bancolombia (extractos) | remitente de extractos documentosbancolombia |

`novedades@`, `mercadeo@`, newsletters del mismo dominio y `no-reply` de promociones NO son movimientos: si filtras por dominio te entran y generas filas falsas. Filtra por remitente exacto.

## 3. Formatos de importe por emisor (test obligatorio antes de escribir)

Davivienda escribe miles con coma y sin decimales (`321,340` = 321.340); Nu escribe `$300.000,00`; Nequi escribe `28.000`. Un mismo número de tres dígitos tras el separador es separador de miles, no decimales.

```python
def parsear_importe(txt):
    if txt is None:
        return None
    t = re.sub(r"[^\d.,]", "", str(txt))
    if not t:
        return None
    if "," in t and "." in t:
        if t.rfind(",") > t.rfind("."):
            t = t.replace(".", "").replace(",", ".")
        else:
            t = t.replace(",", "")
    elif "," in t:
        entero, _, dec = t.rpartition(",")
        t = (entero + "." + dec) if len(dec) != 3 else t.replace(",", "")
    elif "." in t:
        entero, _, dec = t.rpartition(".")
        if len(dec) == 3:
            t = t.replace(".", "")
    try:
        return float(t)
    except ValueError:
        return None
```

Verifica con los tres formatos reales antes de conectarlo a la escritura: `321,340 -> 321340.0`, `28.000 -> 28000.0`, `$300.000,00 -> 300000.0`. Si un monto no parsea, la fila NO se escribe.

## 4. Mapeo correo → pestaña del producto

Identifica por últimos cuatro dígitos cuando el correo los traiga, y cae al remitente solo si el emisor tiene un único producto. Si hay ambigüedad (varios productos del mismo emisor y el correo no trae últimos cuatro), va a pendientes: nunca elijas una pestaña "muy probable".

| Correo | Producto |
|---|---|
| Davivienda, "movimiento de su Tarjeta Crédito terminada en ****N" | `davivienda crédito` (mismo N). El correo trae fecha, hora, `Valor Transacción`, `Clase de Movimiento` y `Lugar de Transacción` |
| Davivienda, movimientos que el correo rotula como `Cta de Ahorros` | `davivienda roja débito`, sin inventar número de tarjeta |
| Nu, "pago ... de tu Tarjeta de crédito" / "Producto destino **** **** **** N" | `NU credito`; el N del correo es el dato real de los últimos cuatro |
| Nu, "Cuenta Nu" / extracto de cuenta | `NU débito`; si solo es el aviso de extracto, a pendientes |
| Nequi, "Recibiste N de <persona> el <fecha>" | `Nequi`, dirección entrada |
| Bancolombia, extracto y avisos sin detalle en el cuerpo | pendientes (requiere abrir el PDF) |

El mismo correo puede describir un pago a la tarjeta de crédito (abono a la deuda) y no un egreso de la cuenta. Registra la dirección según la clase de movimiento del propio correo, no según la intuición.

## 5. Escritura, idempotencia y pendientes

- Fuente de verdad por producto: un JSON bajo `referencia/` (mismo patrón que `fondos.json`), y el build del XLSX recrea la pestaña desde ahí. Ver la regla dura en SKILL.md: la pestaña del XLSX sola se borra en el próximo rebuild.
- Estado de procesados aparte (`referencia/correos_estado.json`): lista de ids de mensaje ya aplicados. Deduplica por id de mensaje Y por clave económica (producto + fecha + monto + concepto normalizado) — el mismo banco reenvía avisos con id nuevo.
- Soporte: guarda el id de mensaje o el asunto en la columna de soporte de la fila. Una fila de banco sin soporte no se puede auditar después.
- Lo que no parsea, lo ambiguo o lo que llega en adjunto va a una cola (`referencia/correos_pendientes.jsonl`) y se reporta al usuario; el script no escribe nada por ese correo en ese ciclo.
- Ejecuta primero en modo `--dry-run` que imprima las filas planeadas y no toque nada. El backfill de meses anteriores se confirma con el usuario: puede chocar con filas ya registradas a mano y duplicarlas.
- Marca o etiqueta en Gmail lo ya aplicado; el estado local sigue siendo la fuente principal de idempotencia.

## 6. Automatización

Job de Hermes con script determinista (sin agente) cada 30 min, con `deliver` para que el resumen llegue al canal del usuario; imprime nada cuando no hay novedades para que no genere ruido. Env sanitizado (`env -u PYTHONPATH`) y `PATH` explícito. Si el token de Gmail falla, el script sale con error sin tocar el JSON: nunca "seguir sin leer" y seguir escribiendo.


## Extractos bancarios (verificado 2026-09-13)

- Los extractos de **Bancolombia, Davivienda y Nu caen en la PAPELERA de Gmail**: hay que leer con `includeSpamTrash=True` (o `in:anywhere`); la búsqueda normal devuelve 0. Gmail vacía la papelera a los **30 días** → descargar los adjuntos apenas lleguen.
- Los PDF vienen **cifrados** (Davivienda, Nu y Bancolombia). La clave vive en `~/.hermes/contabilidad/.extractos_clave` (modo 600, en `.gitignore`); se lee con `pypdf`: `rd = PdfReader(...); rd.decrypt(clave)` → 1/2 = ok. Se extrae texto con `p.extract_text()` (para Nu las tablas salen desordenadas: parsear por anclas y verificar cuadre). Pitfall al leer el texto extraído: el PDF separa en **columnas** etiqueta y valor en **líneas distintas** ("Cupo total" en una línea, el valor en la siguiente; "Abonos − $0,00" encadenado dentro del resumen). Para leer un dato, busca la línea de la etiqueta y toma la línea siguiente que tenga un monto, no asumas que vienen juntas; Nu además escribe el valor antes que la etiqueta ("Tu cupo definido $4.000.000,00").
- Destino de soportes: `soportes/correos/<AAAAMM>/<emisor>/<archivo>.pdf` + su `.txt` con la capa de texto + `soportes/correos/manifiesto_sha256.txt`. **Nunca a Drive** (POLITICA_SOPORTES: destino único RAID); el respaldo a `/mnt/raid/backups/contabilidad_suarez/soportes/` lo hace el backup nocturno.
- Detalles de correo que cambian el mapeo: Davivienda etiqueta la cuenta de ahorros (****7226) como **"Cta de Ahorros"**; Nu crédito = destino ****5127 (origen MSV296) y Nu débito = "Pagaste con tu Cuenta de ahorros Nu"; **Bancolombia solo manda adjuntos** y el producto/periodo van en el nombre: `Extracto_<contrato>_<AAAAMM>_<PRODUCTO>_<NNNN>.pdf` (FIDUCUENTA 4078/4080/4081/9532/9535/9536/9537/0978, RENTA_ACCIONES_LATAM 2187, CONSOLIDADO 6002).
- Los correos de **Nu débito no traen fecha en el cuerpo** (usar la fecha del mensaje) y el 4xmil va como línea aparte cuando es > 0.
- Dedupe: por `msg_id` **y** por clave económica con tolerancia **±1 día** (los correos cruzan medianoche: una compra del 10/09 llegó fechada 11/09 00:01).


## Abonos de tarjeta de crédito (regla del usuario, 13-sep-2026)

Un abono de tarjeta **no es un gasto nuevo**: es una transferencia `fondo -> tarjeta`.
- **Primero el fondo de origen**: la SALIDA se registra en el fondo (`referencia/fondos.json` -> `movimientos[]` si es fondo Nu; libro del fondo si es Renata/Familia) y la ENTRADA como columna `Abono` en la pestaña de la tarjeta, donde **aumenta el cupo disponible**. `Fondo origen` es obligatorio: si no se sabe, la fila queda `Pendiente de fondo` y NO se toca el fondo (nunca asumir "Familia").
- Columnas de pestaña de tarjeta: `Fecha | Concepto | Cargo | Abono | Fondo origen | Cupo disponible | Estado | Soporte`; `Cupo disponible` acumula (`base + abono - cargo`) y se **reancla** con una fila centinela tras cada corte ("Corte <fecha> — cupo disponible según extracto $X").
- La fecha válida del abono es la de **aplicación por el banco** (`Detalle aplicación de pagos y abonos` del extracto), no la del día en que se transfirió.
- **Conciliación al llegar el extracto**: (a) el abono debe aparecer en `Detalle aplicación de pagos y abonos` (si no: `Abono no aplicado — reclamar`); (b) `cupo_total(extracto) - cargos + abonos ≈ cupo_disponible(extracto)` (tolerancia $2 por redondeo); (c) si no cuadra: `Descuadre — revisar` con la diferencia, nunca cuadrar en silencio; (d) el `Cupo total` se toma del extracto, no se supone.
- En el extracto de Nu el campo se llama `Abonos` (dentro del resumen de la deuda); en Davivienda, `-Pagos y abonos` y la sección `Detalle aplicación de pagos y abonos`. Verificar que el pago figure ahí es el chequeo de "¿se aplicó?".
- Trampa ya conocida: `registrar.py` clasifica el concepto `abono` como ENTRADA; nunca usarlo para pagos de tarjeta.

## Log de cambios: va DENTRO del libro, no en archivos sueltos (preferencia del usuario, 13-sep-2026)

Manuel NO quiere documentos sueltos ni depender de archivos externos: todo cambio/plan/registro de la contabilidad se asienta en la hoja `Log de cambios` del propio `contabilidad 2026.xlsx` (columnas `Fecha/hora | Accion | Origen de datos | Integridad`). No crear CHANGELOG.md ni bitácoras aparte; si ya existe un log externo, no añadirle entradas (revertir lo añadido y usar el workbook). Antes de tocar el xlsx, copia de respaldo `.bak_*`. Nombres canónicos de fondos llevan prefijo `Fondo`: `Fondo de aptos, Fondo de emergencia, Fondo universidad Renata, Fondo Moto, Fondo Ahorro, Fondo Auxilios`.
