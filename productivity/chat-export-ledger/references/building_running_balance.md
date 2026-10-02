# Construir el Excel de registro (openpyxl)

Estructura de 3 hojas para el registro contable de Renata (WhatsApp export):

## Hoja "Movimientos" — columnas
`Fecha | Hora | Concepto | Entrada | Salida | Saldo`

### Saldo acumulado POR FÓRMULA (nunca hardcodeado)
- Fila de saldo inicial (primera fila de datos, say r=4):
  `=D4-IF(ISBLANK(E4),0,E4)`
- Filas siguientes (r>4):
  `=F{r-1}+D{r}-IF(ISBLANK(E{r}),0,E{r})`
- Fila TOTALES: `=SUM(D4:Dn)`, `=SUM(E4:En)`, `=F{n}`.

### Formato
- Moneda: `"$"#,##0.00` en Entrada/Salida/Saldo.
- Entradas verde claro (`E2EFDA`), salidas naranja claro (`FCE4D6`), totales azul claro (`D9E1F2`).
- Filas con movimiento sin monto: concepto con `(*)` y nota al pie:
  "Movimiento registrado en el chat sin monto especificado. No afecta el saldo hasta que se confirme."
  La celda Salida queda en blanco → la fórmula la trata como 0.

## Hoja "Resumen"
Saldo total = disponible + CDTs. Cruza disponible vs. suma de CDTs de la hoja 3.

## Hoja "CDTs"
`Vencimiento | Tasa | Capital | Interés a hoy | Total`
- Tasa como fracción con formato `0.00%` (0.096 → 9.60%).
- `Total = Capital + Interés`.
- Total capital debe coincidir con "Invertido en CDT Nu" del Resumen (cross-check).

## Ejemplo real (Renata, 3 AGO 2026)
- Saldo inicial: $1.344.224,85
- +$85.000 (Manuel→fondo), +$125.000 (Manuel→fondo)
- −$125.000 (pasajes Renata), −$210.000 (transferencia comprobante→Renata)
- Saldo final: $1.219.224,85
- CDTs total capital: $1.010.289,28 (4 plazos)
