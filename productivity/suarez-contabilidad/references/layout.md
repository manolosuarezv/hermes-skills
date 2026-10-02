# Layout del libro Familia Suárez 2026

## Estructura
- Hoja `Resumen`: fila por mes (Enero fila 5 … Diciembre fila 16), fila 12 = Agosto 2026.
  - Cols: A=Mes, B=Entra, C=Sale, D=Saldo. Fila 17 = TOTALES (suma B5:B16 / C5:C16 / D).
- 12 hojas mensuales `Enero 2026` … `Diciembre 2026`.
  - Encabezados fila 3: A=Fecha, B=Hora, C=Concepto, D=Entra, E=Sale, F=Saldo, G=Soporte.
  - Datos desde fila 4. Fila final = TOTALES (suma D4:D5…, E4:E5…, F=D-E).

## Plantilla tiene un artefacto
La primera fila de datos del template trae la suma con rango invertido de 1 celda:
`E4 = =SUM(E4:E3)`, `F4 = =F3`. No usar eso como dato. Al insertar movimientos:
- Pon datos en filas 4,5,… y mueve la zona TOTALES a la(s) fila(s) siguiente(s).
- Fórmulas correctas de TOTALES: `D = =SUM(D4:D5)`, `E = =SUM(E4:E5)`, `F = =D-E`.
- Saldo corriente por fila: `F4 = =D4`, `F5 = =F4-D5+E5` (F anterior − Sale + Entra).

## Ejemplo concreto: registro de agosto 2026 (arriendo)
Entrada del usuario: 04 AGO 2026, arriendo 4to piso neto 1.695.818 → Entra; 10% (169.581,80) al fondo mantenimiento → Sale.

Filas resultantes en `Agosto 2026`:
| Fila | Fecha | Concepto | Entra | Sale | Saldo |
|------|-------|----------|-----------|-----------|-----------|
| 4 | 4 | Arriendo 4to piso (familia Suarez) neto | 1695818 | | 1695818 |
| 5 | 4 | Fondo mantenimiento aptos (10% arriendo) | | 169581.8 | 1526236.2 |
| 6 | TOTALES | | =SUM(D4:D5) | =SUM(E4:E5) | =D6-E6 |

Saldo mes = 1.526.236,20. Resumen fila 12: B=1695818, C=169581.8, D==B-C.

Verificación (tras recálculo LibreOffice): `load_workbook(f, data_only=True)` debe dar
Agosto fila 6 = [TOTALES, 1695818, 169581.8, 1526236.2]; Resumen fila 12 = [Agosto 2026, 1695818, 169581.8, 1526236.2].

## Drive / respaldo
- Drive file id (familia): `FILE_ID_FAMILIA` (reconfirmar con files().list si falla).
- Subir: `files().update(fileId=fid, media_body=MediaFileUpload(path, resumable=True), fields='id,webViewLink,modifiedTime')`.
- `modifiedTime` debe avanzar tras subir; si no, la subida no tomó.
- `backup_qbex.py` hace Drive→SCP→git en /mnt/raid/backups/contabilidad_suarez/ (SOLO al final del día).
