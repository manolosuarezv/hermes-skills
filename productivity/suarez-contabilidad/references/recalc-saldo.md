# Recálculo de Saldo (col F) tras insertar filas — llevar el saldo HISTÓRICO

## Regla de oro
Al insertar movimientos y reescribir la columna F (Saldo acumulado), **NUNCA empieces el
saldo de 0 ni de una fila de datos arbitraria**. Carga el ÚLTIMO saldo histórico real (la
fila inmediatamente ANTES de TOTALES, `r_tot-1`, col F) y llévalo hacia adelante fila por
fila. Si no, corrompes TODO el libro (saldo negativo gigante) y dependes de un restore.

## Por qué importa (sesión 24 AGO 2026)
En esta sesión se insertó un préstamo inter-libros (Renata→Familia, ventana $270.000).
La primera recalculación empezó `saldo=0` en la fila 15 → Familia dio **−1.450.904** y
Renata **−100.000**. Segundo intento: `saldo=62901.2` pero recorriendo desde la fila 15
con el bucle mal acotado → Familia **−1.388.002,8**. SOLO funcionó la 3ª versión que
cargó `saldo_hist = float(ws.cell(r_tot-1, 6).value)` y recorrió solo las filas vivas.
Restaurar desde `.bak` salvó los dos primeros intentos fallidos.

## Algoritmo correcto (reutilizable)
```python
import openpyxl

def agregar_con_saldo(path, sheet, filas_nuevas, primera_data=15):
    """Inserta filas antes de TOTALES y recalcula Saldo (col F) llevando el histórico.
    filas_nuevas: lista de dicts {col: valor}. Cols: 1=Fecha 2=Hora 3=Concepto
    4=Entra 5=Sale 6=Saldo 7=Soporte. Devuelve el saldo final."""
    wb = openpyxl.load_workbook(path)
    ws = wb[sheet]
    r_tot = ws.max_row                       # fila TOTALES
    saldo_hist = float(ws.cell(r_tot-1, 6).value or 0)   # <-- CLAVE
    n = len(filas_nuevas)
    ws.insert_rows(r_tot, n)
    saldo = saldo_hist
    for i, fila in enumerate(filas_nuevas):
        rr = r_tot + i
        for c, val in fila.items():
            ws.cell(rr, c).value = val
        try:    e = float(ws.cell(rr, 4).value or 0)
        except: e = 0.0
        try:    s = float(ws.cell(rr, 5).value or 0)
        except: s = 0.0
        saldo += e - s
        ws.cell(rr, 6).value = round(saldo, 2)
    # Recalcular fila TOTALES (Entra/Sale suman desde primera_data; Saldo = saldo final)
    te = ts = 0.0
    r = primera_data
    while True:
        c = ws.cell(r, 3).value
        if c and str(c).strip().upper().startswith("TOTALES"):
            break
        try:    te += float(ws.cell(r, 4).value or 0)
        except: pass
        try:    ts += float(ws.cell(r, 5).value or 0)
        except: pass
        r += 1
    ws.cell(r, 4).value = round(te, 2)
    ws.cell(r, 5).value = round(ts, 2)
    ws.cell(r, 6).value = round(saldo, 2)
    wb.save(path)
    return saldo

# Familia: el préstamo entra y sale (neto 0 -> saldo queda igual)
agregar_con_saldo("contabilidad familia suarez 2026.xlsx", "Agosto 2026", [
    {1: 24, 3: "Prestamo fondo universidad Renata (entra, deuda con Renata)", 4: 270000, 5: None, 6: None},
    {1: 24, 3: "Pago ventana (Ana Sofia Velez - prestamo Renata)",          4: None, 5: 270000, 6: None},
])
# Renata: el préstamo es SALIDA real de su libro (-270k)
agregar_con_saldo("contabilidad Renata suarez 2026.xlsx", "Agosto 2026", [
    {1: "24 AGO 2026", 2: "15:46", 3: "Prestamo a fondo familia Suarez (ventana) - deuda familia con Renata",
     4: 0, 5: 270000, 6: None, 7: "Si (imagen recibida)"},
])
```

## Buenas prácticas
- **Backup ANTES de editar**: `cp <libro>.xlsx "<libro>.bak_$(date +%Y%m%d_%H%M%S).xlsx"`.
  El restore salvó esta sesión dos veces.
- **`primera_data` es específico de la hoja** (Agosto = 15). Para otros meses, ajusta o
  detecta la primera fila con datos no vacíos tras la cabecera.
- Tras insertar, verifica con `load_workbook(path, data_only=True)` que la última fila de
  datos y TOTALES den el saldo esperado ANTES de regenerar el unificado.
- El unificado SOLO se regenera con `build_unificado.py` (lee origen). Correrlo tras editar.

## Restaurar desde .bak cuando el nombre TIENE ESPACIOS
Los respaldos se llaman `contabilidad familia suarez 2026.bak_20260824_205857.xlsx`
(con espacios). Un `for f in $BK` hace word-split por espacio y `cp` falla silenciosamente
("Renata: No such file or directory"). Usar SIEMPRE comillas y `while` con `IFS`:
```bash
while IFS= read -r f; do
  case "$f" in
    *familia*) cp "$f" "contabilidad familia suarez 2026.xlsx" ;;
    *Renata*)  cp "$f" "contabilidad Renata suarez 2026.xlsx" ;;
  esac
done < <(ls -t *.bak_20260824_*.xlsx)
```
