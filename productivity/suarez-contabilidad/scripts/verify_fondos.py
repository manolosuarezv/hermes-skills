#!/usr/bin/env python3
"""
Verificación ad-hoc end-to-end de los saldos de Fondo de aptos.
Lee la fuente de verdad (referencia/fondos.json), regenera el unificado
y valida que la hoja 'Fondo de aptos' y el Resumen coincidan con el saldo
recalculado. NO edita nada; solo valida.

Uso:
  cd /Users/manuelsuarez/.hermes/contabilidad
  ./venv/bin/python3 scripts/verify_fondos.py
Salida: "AD-HOC OK: apertura=... movs=N final=... resumen=..." o AssertionError.
"""
import json
import subprocess
import os
import openpyxl

BASE = "/Users/manuelsuarez/.hermes/contabilidad"
REF = os.path.join(BASE, "referencia", "fondos.json")
XLSX = os.path.join(BASE, "contabilidad 2026.xlsx")
BUILD = os.path.join(BASE, "scripts", "build_unificado.py")
PY = os.path.join(BASE, "venv", "bin", "python3")


def main():
    fa = json.load(open(REF))["fondo_aptos"]
    aper = float(fa["saldo_apertura"])
    movs = fa.get("movimientos", [])
    extra = sum(float(m.get("entra", 0) or 0) - float(m.get("sale", 0) or 0) for m in movs)
    esperado = round(aper + extra, 2)

    r = subprocess.run([PY, BUILD], capture_output=True, text=True)
    assert r.returncode == 0, "build_unificado.py fallo:\n" + r.stderr

    wb = openpyxl.load_workbook(XLSX, data_only=True)
    ws = wb["Fondo de aptos"]
    vals = [[ws.cell(i, c).value for c in range(1, 6)] for i in range(4, 12)]
    assert abs(vals[1][2] - aper) < 0.01, "apertura mal: %s" % vals[1]
    assert abs(vals[-1][4] - esperado) < 0.01, "saldo final mal: %s vs %.2f" % (vals[-1], esperado)

    res = None
    for i in range(1, 15):
        if wb["Resumen"].cell(i, 1).value == "Fondo de aptos (banco Nu)":
            res = wb["Resumen"].cell(i, 2).value
    assert res is not None and abs(res - esperado) < 0.01, "Resumen no cuadra: %s" % res

    print("AD-HOC OK: apertura=%.2f movs=%d final=%.2f resumen=%.2f"
          % (aper, len(movs), esperado, res))


if __name__ == "__main__":
    main()
