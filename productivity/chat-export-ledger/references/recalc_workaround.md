# Recálculo de fórmulas sin recalc.py (Python 3.9)

El `scripts/recalc.py` del skill `xlsx` usa `tempfile.TemporaryDirectory(ignore_cleanup_errors=...)`,
que no existe antes de Python 3.10 → `TypeError: __init__() got an unexpected keyword argument 'ignore_cleanup_errors'`.

## Workaround: LibreOffice headless directo
Recalcula y reescribe el archivo en sitio (igual que recalc.py, pero sin el bug):
```bash
# macOS: ruta del binario
/Applications/LibreOffice.app/Contents/MacOS/soffice --headless \
  --convert-to xlsx --calc --outdir /tmp/recalc_out <archivo>.xlsx

# Linux
soffice --headless --convert-to xlsx --calc --outdir /tmp/recalc_out <archivo>.xlsx
```
Luego copiar el resultado al destino final.

## Verificar valores cacheados
```bash
python3 -c "
import openpyxl
wb = openpyxl.load_workbook('/tmp/recalc_out/<archivo>.xlsx', data_only=True)
ws = wb['Movimientos']
for r in range(4, 12):
    print([ws.cell(r,c).value for c in range(1,7)])
"
```
Spot-check: saldo final acumulado y celdas SUM de totales. Cero errores = verde.

## Prerrequisito
LibreOffice no viene por defecto. Instalar: `brew install libreoffice` (macOS) / `sudo apt install libreoffice` (Linux).
