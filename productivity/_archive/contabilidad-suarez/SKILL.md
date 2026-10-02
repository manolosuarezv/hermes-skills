---
name: contabilidad-suarez
description: Registro contable Suárez/Renata por cualquier canal.
---

# Contabilidad Suárez — Instrucción única para todos los canales

Eres UNA sola instancia de Hermes. La misma memoria y este skill se cargan en la sesión de
CLI, Telegram, WhatsApp y Email. Por eso, registra SIEMPRE igual, sin importar de dónde
llegue el mensaje. No "mezcles" criterios según el canal.

## Archivos (NO tocar a mano fuera de los scripts)
- Libros: `/Users/manuelsuarez/.hermes/contabilidad/contabilidad familia suarez 2026.xlsx`
  y `.../contabilidad Renata suarez 2026.xlsx`
- Drive: cuenta `Manolosuarezv@gmail.com` (token en `drive_token.json`).
- Motor: `registrar.py` (usa el venv: `./venv/bin/python3 registrar.py ...`).
- Logs: `/Users/manuelsuarez/.hermes/contabilidad/logs/contabilidad.log.jsonl`.

## Formato del xlsx (respetar SIEMPRE)
- Hoja `Resumen` + 12 hojas mes (`Enero 2026` ... `Diciembre 2026`).
- Columnas por movimiento: `A=Fecha, B=Hora, C=Concepto, D=Entra, E=Sale, F=Saldo, G=Soporte`.
- El usuario NO da hora → dejar columna B vacía.
- El Saldo (F) es un saldo corriente calculado por `registrar.py` (no confiar ciegamente en
  fórmulas de plantilla; el script lo escribe como valor).

## REGLAS OBLIGATORIAS
1. **NO mezclar libros**: Renata es independiente de Familia Suárez. Cada mensaje va a su libro.
2. **Dirección del monto**: un número con `-` o palabras "pagué/gasté/compré/salió/egreso" =
   SALIDA (col E). Con `+` o "recibí/ingresó/entró/deposité/cobré" = ENTRADA (col D).
   Si el mensaje trae monto positivo sin señal ni verbo, asumir SALIDA por defecto y, si hay
   duda, confirmar con el usuario antes de escribir.
3. **Soporte ≠ movimiento**: si el usuario dice "comprobante 210.000" o "soporte 210000", eso es
   el NÚMERO DEL SOPORTE (col G), NO un movimiento. Guardarlo en la columna Soporte del
   movimiento correspondiente; no crear fila de dinero por eso.
4. **Arriendo 4to piso (Familia Suárez)**: cuando entra el arriendo, el monto NETO va a Entra
   (col D) y SE GENERA AUTOMÁTICAMENTE una segunda fila "Fondo mantenimiento aptos (10% arriendo)"
   como SALIDA (col E) por el 10% del neto, mismo día. `registrar.py` ya hace esto; no repetir
   a mano.
5. **Mes correcto**: la hoja se elige por la FECHA del movimiento, no por `datetime.now()`.
   "07-ago" va a `Agosto 2026` aunque hoy sea otro mes.

## Cómo registrar (desde cualquier canal)
El usuario puede escribir lenguaje natural. Tú parses y llamas al script:
```
cd /Users/manuelsuarez/.hermes/contabilidad
./venv/bin/python3 registrar.py familia "07-ago mercado -45000 soporte 12345"
./venv/bin/python3 registrar.py renata "ayer recibí 200000 arriendo"
./venv/bin/python3 registrar.py familia "hoy arriendo 4to piso 1695818"
```
- Formatos de fecha aceptados: `DD-mmm` (07-ago), `DD-mmm-AAAA`, `hoy`, `ayer`, o día/mes/año.
- Montos en notación CO: `45.000` = 45000, `1.695.818` = 1695818, `45,50` = 45.50.
- El script responde con fila(s) escritas, saldo antes/después y link de Drive. Reenvía ese
  resumen al canal como confirmación.

## Confirmación a todos los canales
Después de registrar, responde en el mismo canal con un resumen corto:
`✓ Familia | 07-ago mercado -$45.000 (sop 12345) | saldo $X`. Esto cumple "los canales que
reciben datos tienen updates de los registros".

## Backup diario + digest (cron)
Un cron diario (`backup_qbex.py`) descarga de Drive, hace SCP al qbex (server01 192.168.1.69)
en `/mnt/raid/backups/contabilidad_suarez/backup/`, commit git + tag por fecha, y poweroff.
Además genera un digest de los cambios del día (del log JSONL) y lo difunde a los canales
conectados. Si un canal no está conectado, se omite sin error.

## Pitfalls
- `registrar.py` original escribía el monto en la col C sin separar Entra/Sale y sin Saldo:
  YA ESTÁ CORREGIDO en esta versión. No usar la lógica vieja.
- No inventar movimientos ni saldos. Si falta datos, pregunta.
- No borrar ni reordenar filas existentes. Solo agregar al final (el script inserta antes de
  la fila TOTALES).
- Si el Drive falla (token expirado), reporta el error; no simules éxito.
- La regla "no inventar" aplica también al LEER/AGREGAR datos (p.ej. Portafolio Trii): nunca insertes un ticker o monto que no esté en el libro, ni cambies la etiqueta de un ticker por otro que el modelo crea reconocer. Ver `suarez-contabilidad` (integridad de datos / Portafolio Trii).
- **El entorno del cron envenena el venv (cryptography)**: el gateway/cron de Hermes exporta `PYTHONPATH=/Users/manuelsuarez/.hermes/hermes-agent:/Users/manuelsuarez/.hermes/hermes-agent/venv/lib/python3.11/site-packages`. Al correr los scripts de contabilidad (`BASE/venv/bin/python3`, py3.9) ese path se inyecta ANTES del site-packages propio y `import cryptography` carga la versión 3.11 dentro de py3.9 → `ImportError: dlopen(...cryptography..._rust.abi3.so): symbol not found in flat namespace '_PyType_GetName'`. Solo afecta a `backup_qbex.py` y `digest_diario.py` (importan google/cryptography); `registrar.py` NO importa cryptography y funciona igual. **Fix**: correr con `env -u PYTHONPATH ./venv/bin/python3 scripts/<script>.py`, o asegurar que el script sanee el entorno. `cierre_diario.py` ya trae `_clean_env()` que quita `PYTHONPATH` en los subprocess. Detalle y receta en `references/cron-venv-pythonpath-pitfall.md`.
- **Firma del Drive token expirado/revocado**: si `backup_qbex.py` cae con `google.auth.exceptions.RefreshError: ('invalid_grant: Token has been expired or revoked.', ...)`, el `drive_token.json` está revocado. NO es error de red ni de qbex. Requiere re-autenticación OAuth manual del usuario (no automatizable desde cron). Reporta el fallo exacto; el log queda con `"drive_link": "(local) sin Drive: token revocado, no subido"`.
