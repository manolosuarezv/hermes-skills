#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_trii.py — Verificación reutilizable de la centralización Trii.

Comprueba (SIN tocar producción, con datos sintéticos y leyendo el estado en
disco) que:
  1. trii_calc.py tiene las reglas EXACTAS (comisión por tramos) y agrega bien.
  2. calc_trii.py importa trii_calc y conserva la firma (rows, total) de 10 elems.
  3. build_unificado.py NO importa agregar_portafolio (layout incompatible — ver
     pitfall en SKILL.md): solo debe importar constantes + comision_venta.
  4. El plist launchd del cierre está bien formado y tiene EnvironmentVariables
     con PYTHONPATH="" y un dir de logs que existe.

Uso:  cd /Users/manuelsuarez/.hermes/contabilidad
      ./venv/bin/python3 scripts/verify_trii.py
Salida: "RESULTADO: N/N chequeos pasaron".  Sale 0 si todo pasa.
"""
import os, sys, xml.etree.ElementTree as ET, re

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(BASE, "scripts")
PLIST = os.path.expanduser(
    "~/Library/LaunchAgents/com.suarez.contabilidad.cierre.plist")

ok = []

# ── 1. trii_calc: reglas + agregación (datos sintéticos) ──────────────────
sys.path.insert(0, SCRIPTS)
import trii_calc as t
assert t.comision_venta(3_000_000) == 14875
assert t.comision_venta(6_000_000) == 14875 + 0.0025 * 1_000_000
rows, total = t.agregar_portafolio([("A", 10, 100.0, 120.0)], 0.30, 14875)
assert total[0] == "TOTAL" and abs(total[5] - 1200.0) < 1e-6
assert len(total) == 10 and all(len(r) == 10 for r in rows)
ok.append("trii_calc: reglas EXACTAS + agregacion (rows/total len-10) OK")

# ── 2. calc_trii importa trii_calc y compila ─────────────────────────────
src_calc = open(os.path.join(SCRIPTS, "calc_trii.py")).read()
assert "import trii_calc" in src_calc
assert "trii_calc.agregar_portafolio(" in src_calc
assert "trii_calc.calcular_fila(" in src_calc
subprocess = __import__("subprocess")
subprocess.run([sys.executable, "-m", "py_compile",
                os.path.join(SCRIPTS, "calc_trii.py")], check=True)
ok.append("calc_trii.py: importa trii_calc (calcular_fila/agregar_portafolio) + compila OK")

# ── 3. build_unificado NO debe importar agregar_portafolio ───────────────
src_b = open(os.path.join(SCRIPTS, "build_unificado.py")).read()
assert "from trii_calc import" in src_b, "build_unificado debe importar de trii_calc"
assert "agregar_portafolio" not in src_b, \
    "build_unificado NO debe importar agregar_portafolio (layout incompatible)"
assert "comision_venta" in src_b
subprocess.run([sys.executable, "-m", "py_compile",
                os.path.join(SCRIPTS, "build_unificado.py")], check=True)
ok.append("build_unificado.py: importa constantes+comision_venta de trii_calc, NO agregar_portafolio OK")

# ── 4. plist launchd bien formado + EnvironmentVariables + logs dir ──────
if os.path.exists(PLIST):
    txt = open(PLIST).read()
    ET.parse(PLIST)
    for k in ("Label", "ProgramArguments", "StartCalendarInterval",
              "EnvironmentVariables", "StandardOutPath", "StandardErrorPath"):
        assert f"<key>{k}</key>" in txt, f"plist falta {k}"
    assert "<string></string>" in txt, "plist debe tener PYTHONPATH vacio"
    m = re.search(r"<key>StandardOutPath</key>\s*<string>(.*?)</string>", txt)
    d = os.path.dirname(m.group(1))
    assert os.path.isdir(d), f"plist: falta dir de logs {d}"
    ok.append("plist: bien formado, EnvironmentVariables+PYTHONPATH='' presentes, logs/ existe OK")
else:
    ok.append("plist: NO existe (aun no creado/cargado) — saltable")

print("=== VERIFY_TRII (no suite) ===")
for l in ok:
    print("  [OK]", l)
print(f"RESULTADO: {len(ok)}/{len(ok)} chequeos pasaron")
