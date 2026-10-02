# referencia/fondos-json.md — fuente de verdad de los fondos Nu (Fondo de aptos / Fondo de emergencia)

Ubicación: `/Users/manuelsuarez/.hermes/contabilidad/referencia/fondos.json`

Los saldos REALES de los fondos bank Nu (Fondo de aptos, Fondo de emergencia) NO son
libros xlsx: son saldos de cuenta que el usuario manda por WhatsApp. `build_unificado.py`
LOS LEE y los vuelca al unificado (`contabilidad 2026.xlsx`). `fondos.json` es su única
fuente de verdad.

## Esquema (desde 18 AGO 2026)
```json
{
  "fondo_aptos": {
    "banco": "Nu",
    "saldo_apertura": 308559.01,
    "fecha": "14 AGO 2026",
    "nota": "...",
    "movimientos": [
      {"fecha": "18 AGO 2026", "detalle": "Mercado para Sofia (gasto aptos)", "entra": 0, "sale": 100000.00},
      {"fecha": "18 AGO 2026", "detalle": "Arriendos/nomina (neto: ...)", "entra": 1027372.00, "sale": 0}
    ]
  },
  "fondo_emergencia": { "banco": "Nu", "saldo_apertura": 304241.81, "fecha": "14 AGO 2026", "nota": "...", "movimientos": [] }
}
```

`build_unificado.py` calcula:
`fondo_aptos_real = saldo_apertura + sum(m["entra"] - m["sale"] for m in movimientos)`

Y REPRODUCE esos `movimientos` en:
- (a) bloque `FONDO DE APTOS` del Resumen (hoja "Resumen")
- (b) pestaña `Fondo de aptos`
El espejo 10% arriendos (viene de Familia) va DEBAJO como referencia; ya está incluido
en `saldo_apertura`, NO se suma otra vez.

## PITFALL al volcar en la hoja
La fila "Saldo de apertura" debe usar `_fa_aper` (la apertura plana), NO
`fondo_aptos_real` (el recalculado). El acumulado `_cum` arranca en `_fa_aper` y corre
con cada movimiento. Si usas `fondo_aptos_real` como apertura, la fila de apertura
muestra el saldo FINAL (duplicado) en vez del inicial. Detectado y corregido 18 AGO 2026.

## CÓMO registrar un movimiento de Fondo de aptos
Añade un dict al array `movimientos` en `fondos.json` (con `fecha`, `detalle`, `entra`,
`sale`) y corre `build_unificado.py`. NUNCA lo insertes a mano en el xlsx unificado:
el rebuild lo borra. Esto reemplaza el workaround histórico de "re-insertar post-rebuild".

## Verificación ad-hoc (tras editar, antes de declarar listo)
SCRIPT REUTILIZABLE (desde 18 AGO 2026): `scripts/verify_fondos.py`. Hace TODO el
pipeline en un solo paso y tira AssertionError si algo no cuadra:
```bash
cd /Users/manuelsuarez/.hermes/contabilidad
./venv/bin/python3 scripts/verify_fondos.py
# -> AD-HOC OK: apertura=308559.01 movs=6 final=1102531.01 resumen=1102531.01
```
Correrlo tras CADA edición de `fondos.json` (añadir/quitar movimiento) antes de
commitear. NO reescribas el snippet inline: el script ya lee `fondos.json` ->
regenera unificado -> valida hoja `Fondo de aptos` + Resumen.

Snippet crudo (solo para depurar a mano; el `terminal` SÍ escribe en
/private/var/folders/.../T vía heredoc, el tool `write_file` NO):
```python
import json, subprocess, os, openpyxl
BASE="/Users/manuelsuarez/.hermes/contabilidad"
fa=json.load(open(BASE+"/referencia/fondos.json"))["fondo_aptos"]
aper=float(fa["saldo_apertura"]); movs=fa.get("movimientos",[])
extra=sum(float(m.get("entra",0) or 0)-float(m.get("sale",0) or 0) for m in movs)
esp=round(aper+extra,2)
r=subprocess.run([BASE+"/venv/bin/python3",BASE+"/scripts/build_unificado.py"],capture_output=True,text=True)
assert r.returncode==0, r.stderr
wb=openpyxl.load_workbook(BASE+"/contabilidad 2026.xlsx",data_only=True)
ws=wb["Fondo de aptos"]
vals=[[ws.cell(i,c).value for c in range(1,6)] for i in range(4,11)]
assert abs(vals[1][2]-aper)<0.01 and abs(vals[-1][4]-esp)<0.01
print("OK apertura=%.2f final=%.2f"%(aper,esp))
```

## Histórico
Antes del 18 AGO 2026 el saldo de Fondo de aptos se perdía en cada rebuild porque no tenía
fuente propia; el workaround era re-insertar a mano post-rebuild. ESE WORKAROUND ESTÁ
OBSOLETO desde que `fondos.json` lleva `movimientos[]`.
