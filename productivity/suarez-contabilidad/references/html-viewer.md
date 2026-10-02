# Vista HTML de revisión (solo lectura) — contabilidad Suárez

Generar un HTML consolidado desde `contabilidad 2026.xlsx` (unificado) para que el
usuario REVISE todas las pestañas sin abrir Excel ni tocar los datos. Nació de la
pregunta del usuario (15 AGO 2026): "quiero ver primero el html con los resúmenes de
las pestañas y los movimientos". Patrón probado y ya en disco.

## Cuándo usar HTML vs xlsx (decisión del usuario)
Respuesta que se le dio y el usuario aceptó:
- **xlsx = fuente de verdad** (edición a mano o vía scripts, respaldo a NAS/qbex).
- **HTML = capa de revisión** generada, de solo lectura, abierta con file:// (sin
  servidor, sin nube). Se regenera cuando cambian datos; NUNCA escribe de vuelta.
- **Log/bitácora = texto** (CHANGELOG.md + git) para auditoría diff-able, no dentro del xlsx.
- Consumo de tokens: trabajar el xlsx con openpyxl sale caro y propenso a corrupción
  (ver PITFALLS del SKILL.md: hoja "test" suelta, "RESUMEN POR ACCIÓN" mutado). El HTML
  se genera una vez y el usuario lo lee barato. A la larga el visor cuesta menos tokens
  que depurar el xlsx a cada paso, pero el xlsx sigue siendo el almacén editable.

## Artefactos actuales (en disco)
- Generador: `/Users/manuelsuarez/.hermes/contabilidad/scripts/gen_vista_completa.py`
- Salida: `/Users/manuelsuarez/.hermes/contabilidad/vista_contabilidad_2026.html`
- Comando: `cd /Users/manuelsuarez/.hermes/contabilidad && source venv/bin/activate &&
  python3 scripts/gen_vista_completa.py`

## Estructura del HTML (secciones)
1. KPIs: Patrimonio total + saldo por cuenta (Familia, Renata, Trii valor mercado,
   Fondos de aptos/emergencia).
2. Resumen patrimonial (tabla Cuenta | Saldo actual).
3. Una `<section>` por cuenta con sus movimientos: Familia Suarez, Renata Suarez,
   Trii (movimientos de capital + portafolio actual), Fondo de aptos, Fondo de
   emergencia, Log de cambios.

## Gotchas del script (ya resueltos, no repetir)
- `money_cols` en `table()` debe ser tupla/set: pasar `(1,)` NO `(1)`. `i in money_cols`
  revienta si `money_cols` es int. Mejor: `mc = set(money_cols)` y comparar `i in mc`.
- Formato de miles colombiano: `f"${v:,.2f}".replace(",","X").replace(".",",").replace("X",".")`
  → "$2.700.806,00". Los checks de verificación deben buscar el string CON punto de
  miles ("304.241,81"), no sin formato ("304241,81").
- La nota "Sin NUTRESA (confirmado)" contiene la palabra NUTRESA; un check
  `NUTRESA not in html` da falso positivo. Validar en cambio `not re.search(r"<td>NUTRESA</td>", html)`
  (que no sea fila de portafolio).
- openpyxl lee el unificado con `data_only=True`; las tablas se reconstruyen iterando
  filas y detectando encabezados por la presencia de "Fecha"/"Detalle".

## Verificación ad-hoc del HTML (no suite)
Script temporal en `/tmp` (o `tempfile.mkstemp(dir=$TMPDIR)`), corre y BORRA tras la
corrida. Checks mínimos: DOCTYPE, "Patrimonio 5.499.696,87", "NUCO" presente,
"NUTRESA" NO es fila, secciones Familia/Renata/Fondos/Log presentes, `html.count("<table>")>=6`.
Ver PATCH_LOG del build: el HTML del 15 AGO pasó 10/10.
