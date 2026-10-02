# Renata workbook: hand-edit without breaking build_unificado.py

`build_unificado.py` → `leer_renata()` reads each Renata monthly sheet, returning
tuples `(mes, fecha, concepto, entra, sale, saldo)` where `saldo` = **column F (index 5)**.
`ren_saldo = ren[-1][5]` (the TOTALES row's col F) feeds the final
`print("[ok] saldos Fam=%.2f Ren=%.2f ..." % (..., ren_saldo, ...))`.

If any movement row OR the TOTALES row has col F = None (or a non-numeric string),
the build raises `TypeError: must be real number, not NoneType` and aborts —
leaving the unified workbook stale. Symptom: `[ok] leido Fam=... Ren=...` prints
fine, then the crash on the saldos print line.

## Why it happens
When you `insert_rows` / rewrite the TOTALES row on a Renata monthly sheet with
openpyxl, the newly created cells in column F are empty (None). `leer_renata`
does NOT compute the saldo — it trusts col F. So the last row (TOTALES) yields
`ren_saldo = None`, and `%.2f % None` raises.

## Safe hand-edit recipe (openpyxl)
After inserting/rewriting rows in a Renata monthly sheet, recompute col F for
every row from the "Saldo inicial" anchor:

```python
import openpyxl
path = "contabilidad Renata suarez 2026.xlsx"
wb = openpyxl.load_workbook(path)
ws = wb["Agosto 2026"]           # cambia el mes según corresponda

def f(v):
    try: return float(v)
    except: return 0.0

saldo = None
for r in range(1, ws.max_row + 1):
    c = ws.cell(row=r, column=3).value
    if c is None:
        continue
    if str(c).startswith("Saldo inicial"):
        saldo = f(ws.cell(row=r, column=4).value)
        ws.cell(row=r, column=6).value = saldo   # col F = Saldo
        continue
    if c == "TOTALES":
        ws.cell(row=r, column=6).value = saldo   # col F = saldo final acumulado
        continue
    e = f(ws.cell(row=r, column=4).value)
    s = f(ws.cell(row=r, column=5).value)
    if saldo is None:
        saldo = 0.0
    saldo += e - s
    ws.cell(row=r, column=6).value = saldo

wb.save(path)
```

Then run `./venv/bin/python3 scripts/build_unificado.py` and confirm the
`[ok] saldos ... Ren=...` line prints **without** a TypeError. If it still
crashes, re-check that TOTALES and every movement row have a numeric col F.

## Notes
- The Renata book is NOT a pure entra/sale ledger: `build_unificado.py` reads the
  accumulated Saldo from col F (it does not sum entra−sale itself for the patrimonio).
  So col F is load-bearing — never leave it None.
- Manual edits can leave strings in D/E (Entra/Sale); coerce with `f()` so the
  running saldo math doesn't throw `unsupported operand type(s) for -: 'str' and 'str'`.
- Prefer this script over hand-editing col F per row; a single missed row silently
  zeroes or None's the saldo and breaks the next build.
