# Portafolio Trii — estructura y reglas (sesión 15 AGO 2026)

## Hoja `Portafolio Trii` (libro ORIGEN: `contabilidad familia suarez 2026.xlsx`)
Columnas (fila 4 = encabezado):
- A Empresa · B Fecha compra · C Acciones · D Precio compra/acción
- E Comisión compra · F Costo total lote · G Costo prom/acción (DERIVADA, fórmula)
- H Precio actual/acción · I Valor actual (DERIVADA, fórmula) · J Ganancia % real (DERIVADA, fórmula)
- K Comisión venta est. (DERIVADA, fórmula) · L Precio venta objetivo/acción (DERIVADA, fórmula) · M Estado vs objetivo (DERIVADA, fórmula)

Bloques en la misma hoja:
- **Lotes**: filas 5..N (un ticker puede repetirse en varios lotes: ICOLCAP x2, MINEROS x2).
- Fila centinela `TOTAL` (acciones totales, costo total, valor total).
- Luego `RESUMEN POR ACCIÓN` (agregado por ticker) y `POSICIONES CERRADAS`.

Parámetros (celdas B1 margen objetivo, D1 comisión base) leídos por `calc_trii.py` y `build_unificado.py`:
- margen objetivo = 30% · comisión base = 14.875 · umbral = $5.000.000 · exceso = 0,25% sobre lo que pase de $5M.
- Precio objetivo/acción = (costo_total·(1+margen) + comisión_est) / acciones.
- Comisión est. = comisión_base si valor ≤ umbral, sino comisión_base + 0,25%·(valor − umbral).

## Libro UNIFICADO `contabilidad 2026.xlsx` — pestaña `Trii`
- Arriba: MOVIMIENTOS (capital depositado − retirado; rechazados no suman) — 43 filas.
- Abajo: PORTAFOLIO ACTUAL (valor de mercado) agregado por ticker (14 empresas + TOTAL).
- El valor Trii se lleva al Resumen del unificado como `Trii (valor mercado)` = $2.700.806 (integrado en patrimonio, SIN el sello "[PENDIENTE]").

## TOTALES reales 15 AGO 2026
- 16 lotes / 14 empresas · 260 acciones · costo $2.188.286,59 · valor $2.700.806,00 · +23,4%.
- Empresas: BVC, PFCORFICOL, PFAVAL, ICOLCAP, EXITO, PFGRUPSURA, CELSIA, MINEROS, CIBEST, ECOPETROL, PFDAVVNDA, NUCO, TERPEL, GEB.

## Lección de integridad (sesión 15 AGO)
El agente leyó `NUCO` y lo reportó como "Nutresa", inventando además 4 acc / $44.100 / $11.050
que NO existían. El usuario corrigió: "Nutresa? yo no tengo a el grupo nutresa en mi portafolio".
NUNCA inventar un ticker/holding/número al leer o derivar; si un ticker no se reconoce, verificar la
celda real y, si hay duda, preguntar. La etiqueta del analista nunca se presenta como dato del libro.
