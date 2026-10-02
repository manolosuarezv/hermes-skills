# Corrección de datos erróneos en el ORIGEN (Familia / Renata)

## Cuándo aplica
El libro ORIGEN (`contabilidad familia suarez 2026.xlsx` o el de Renata) puede
tener datos erróneos que el unificado (`contabilidad 2026.xlsx`) SOLO COPIA:
duplicados de un mismo abono, filas de prueba, borradores huérfanos. Corregir
solo el unificado es inútil: `scripts/build_unificado.py` lo regenera leyendo el
origen, así que el error vuelve en la próxima regeneración. Por eso, al hallar un
dato erróneo EN EL ORIGEN, la corrección permanente va al origen. Esto es la
EXCEPCIÓN documentada a la regla "openpyxl nunca reescriba origen; solo genera
copia unificada regenerable" (esa regla rige para el flujo normal de registro, no
para enmendar un dato malo que vive en el origen).

## Protocolo (orden obligatorio)
1. Respaldo con timestamp:
   `cp ORIGEN ORIGEN.bak_origen_$(date +%Y%m%d %H%M%S)`
   (usar `date +%Y%m%d_%H%M%S` sin espacios).
2. Localizar la(s) fila(s) errónea(s) en la hoja mensual correcta (p.ej. `Agosto 2026`).
3. Si la columna Saldo (F) trae VALORES estáticos (no fórmulas vivas):
   - `ws.delete_rows(fila, 1)`.
   - Recalcular la cadena en Python:
     ```python
     def f(v):
         try: return float(v)
         except (TypeError, ValueError): return 0.0
     saldo = 0.0
     for r in range(primera, ultima+1):
         saldo += f(ws.cell(r,4).value) - f(ws.cell(r,5).value)
         ws.cell(r, 6, round(saldo, 2))
     ```
   - Reescribir la fila TOTALES (última): `Entra=sum(col D)`, `Sale=sum(col E)`,
     `Saldo=Entra-Sale`.
4. Regenerar: `python3 scripts/build_unificado.py` (unificado + nota Obsidian) y
   `python3 scripts/gen_vista_completa.py` (HTML de solo lectura).
5. Registrar en `CHANGELOG.md` (sección REGISTRO DE MOVIMIENTOS, arriba): respaldo,
   efecto en saldos/patrimonio y verificación de 3 niveles.
6. VERIFICAR en 3 niveles (origen / unificado / HTML) que el dato ya no aparece y
   que los totales cuadran (ver receta abajo).

## Marcador de datos de prueba
Las filas de prueba NO llevan "prueba" en el Concepto (col C). Están marcadas en
la **columna 2 (Hora)** con texto `"prueba ..."` (p.ej. "prueba sistema",
"prueba mac", "prueba arch"). `build_unificado.py` las separa como `fam_pruebas` y
NO las suma al saldo, pero ensucian la vista. Para borrarlas del origen:
```python
prueba = [i for i in range(1, ws.max_row+1)
          if isinstance(ws.cell(i,2).value, str)
          and "prueba" in ws.cell(i,2).value.lower()]
for i in sorted(prueba, reverse=True):
    ws.delete_rows(i, 1)
```
No contabilizan, así que borrarlas NO cambia el patrimonio; confírmalo igual.

## Cargos idénticos mismo día sin soporte → NO borrar a ciegas
Si aparecen N cargos iguales el mismo día (p.ej. 3 × "sale pago luz" 50.000) y la
columna Soporte (col G) está vacía y no hay referencia a factura / proveedor /
medidor en ninguna hoja del libro: es patrón de posible duplicación de digitación.
NO borrar sin confirmar. Flujo:
  (a) investigar el origen del cobro y la existencia de soporte (PDF, factura);
  (b) si no hay trazabilidad, PREGUNTAR al usuario — ¿fue 1 pago real y 2
      duplicados?, ¿o validar los 3 con el soporte?;
  (c) dejar documentado en CHANGELOG como PENDIENTE y NO modificar hasta decisión.
Regla de negocio ya vigente: el libro lleva el saldo contable; la cuenta real puede
diferir por cobros bancarios (4xmil, cuotas) que el usuario reporta aparte.

### Patrón real observado (Agosto 2026): 3 × "sale pago luz" 50.000
- En `Agosto 2026` filas 17-19: tres cargos idénticos "sale pago luz" de 50.000
  el MISMO día (14 AGO), sin soporte (col G vacía).
- La luz/servicios YA estaba registrada como
  `"Pago servicios publicos EPM (06 AGO 2026)"` (237.650, fila 6). Los 3 de 50.000
  eran duplicados que "se filtraron" (sumaban 150.000 y hundían el saldo).
- El usuario confirmó borrarlos ("el saldo coincide si estos se van"). Borrarlos
  subió el saldo Familia de -88.098,80 a +61.901,20 y el patrimonio unificado
  4.569.732,87 -> 4.719.732,87.
- Si vuelve a aparecer este patrón, la señal es: 3 cargos iguales mismo día +
  ya existe un "Pago servicios publicos EPM" en el mes => borrar los 3 sin
  reconsiderar, PERO siempre dejar respaldo + CHANGELOG + verificación 3 niveles.

## Verificación ad-hoc (sin tocar producción)
Ejecutar el script corrector SOBRE UNA COPIA del `.bak`, no sobre el origen ya
corregido, para confirmar reproducibilidad y no depender de "fe":
```python
import tempfile, shutil, subprocess, sys, openpyxl, os
TMP = "/private/var/folders/w7/fbww9dh93jnb4jpq768khv4r0000gn/T"  # execute_code tempfile SÍ escribe aquí
root = tempfile.mkdtemp(prefix="hermes-verify-", dir=TMP)
xlsx = os.path.join(root, "contabilidad familia suarez 2026.xlsx")
shutil.copy(BAK, xlsx)                                   # BAK = ruta del .bak_origen_*
shutil.copy(os.path.join(BASE,"scripts",script), os.path.join(root,"scripts",script))
r = subprocess.run([sys.executable, os.path.join(root,"scripts",script)],
                   capture_output=True, text=True)
assert r.returncode == 0
wb = openpyxl.load_workbook(x, data_only=True)          # abrir y assert resultados
shutil.rmtree(root, ignore_errors=True)
```
Nota: la herramienta `write_file` del agente NO puede escribir en
`/private/var/folders/.../T`, pero `tempfile.mkdtemp` dentro de `execute_code` SÍ.
Usar ese patrón para verificación efímera.

## Plantillas reutilizables (scripts/ del proyecto)
- `scripts/corregir_dup_nomina.py` — borra fila duplicada de nómina, reconecta la
  cadena Saldo y la fila TOTALES. Adaptar `ws.delete_rows(N,1)` y el rango según el
  caso concreto.
- `scripts/borrar_pruebas_enero.py` — borra las filas donde col2 contiene "prueba".
- `scripts/borrar_pagos_luz.py` — borra N filas con concepto exacto "sale pago luz",
  recalcula la cadena Saldo (Agosto arranca en 0) y la fila TOTALES. Usar como modelo
  para borrar cualquier cargo duplicado idéntico: localizar por concepto exacto,
  `delete_rows` de abajo hacia arriba, reescribir Saldo col6 y TOTALES.
