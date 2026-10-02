# Drive revocado (invalid_grant) — flujo local-only

Cuando `registrar.py` falla con `invalid_grant`, NO se puede descargar ni
subir a Drive. El xlsx LOCAL en `/Users/manuelsuarez/.hermes/contabilidad/`
es la copia de trabajo y sigue al día. Procedimiento que funcionó el
14 AGO 2026:

## 1. Registrar sin Drive
Opción A — script ya existente en el repo de contabilidad:
```
cd /Users/manuelsuarez/.hermes/contabilidad
./venv/bin/python3 scripts/registrar_local.py familia "DD-mmm concepto MONTO"
```
`registrar_local.py` es copia de `registrar.py` con las funciones de
descarga/subida de Drive convertidas en no-ops.

Opción B — edición directa con openpyxl (si no existe registrar_local.py):
copiar `registrar.py` a `registrar_local.py` y dejar las llamadas a
Drive como no-ops, o bien editar el `.xlsx` a mano con openpyxl:
```python
import openpyxl
wb = openpyxl.load_workbook("contabilidad familia suarez 2026.xlsx")
ws = wb["Agosto 2026"]
# insertar fila antes de TOTALES; col F=Entra, G=Sale, H=Saldo
wb.save("contabilidad familia suarez 2026.xlsx")
```

## 2. Regenerar unificado (build_unificado.py es local-only por diseño)
```
./venv/bin/python3 scripts/build_unificado.py
```
Genera `contabilidad 2026.xlsx` leyendo solo los dos xlsx origen.
NO necesita Drive. (Ver fixes de TOTALES/Trii en SKILL.md.)

## 3. Reautenticar Drive y subir
```
./venv/bin/python3 scripts/reauth_drive.py
```
Abre el navegador, elige la cuenta, autoriza, pega el `code=`. Luego
`registrar.py` / `build_unificado.py` vuelven a subir solos (build_unificado
sube el unificado; registrar.py sube el origen).

## Nota
El unificado generado local es válido aunque no se haya subido a Drive.
Solo falta el push. No reportes "Drive al día" hasta confirmar la reauth.
