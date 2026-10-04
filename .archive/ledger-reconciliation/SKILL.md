---
name: ledger-reconciliation
description: "Reconcile personal ledgers from screenshots."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Accounting, Bookkeeping, Excel, OCR, Personal-Finance, Ledger]
    category: finance
---

# Ledger Reconciliation

Maintain split accounting ledgers (e.g. family + child) fed by receipts/screenshots arriving through chat, keep a unified master workbook in sync via a build script, and push the updated books to cloud storage. Built for a recurring monthly bookkeeping cadence where the **source of truth is the per-ledger .xlsx file** and the unified file is *derived*.

## When to Use
- User sends banking/fund screenshots (Nu, Nequi, bank apps) or receipt photos and wants them recorded as ledger entries.
- Multiple ledgers must roll up into one "unificado" workbook with a totals/patrimonio summary.
- Cloud backup of the ledgers is part of the flow (Drive/Dropbox).

## Core Rule: Source of Truth vs Derived
- **Edit the source ledger files directly** (openpyxl). Never hand-edit the unified workbook.
- **Regenerate the unified workbook** with a build script (`build_unificado.py` pattern) that mirrors each source sheet + a `referencia/fondos.json` of fund balances. The build script is the only writer of the unified file.
- Fund/account *balances* that come from screenshots live in `referencia/fondos.json`, **not** as ledger rows — a balance is a point-in-time value, not a transaction. Don't double-count (e.g. if a fund balance already includes a 10% transfer, don't also add the transfer as a movement).
- Patrimonio total = sum of all block balances. Print it in the summary sheet.

## Reading Banking Screenshots (OCR)
Use `tesseract` — the local vision path is unreliable for these. Spanish: `-l spa`.

```bash
tesseract img.jpg stdout -l spa 2>/dev/null | grep -v '^$'
```

**Disambiguate amounts with TSV coordinates** — mobile app screenshots stack several numbers (Total / Disponible / Invertido / rendimiento) and naive text order misassigns them. Pull coordinates and reason about position:

```bash
tesseract img.jpg stdout -l spa tsv 2>/dev/null \
  | awk -F'\t' '$12!="" {print $7, $8, $12}'   # left, top, text
```

Then map by vertical position: a label like `Disponible siempre` at top Y, its value at the same Y to the left, and a *second* value further right at the same Y is a different figure (often a sub-balance or a sibling account) — **ask the user which one is the intended balance before recording it.** See `references/nu-screenshot-ocr.md` for a worked example.

Never treat a screenshot's "Total" and "Disponible" as the same number without checking — they differ when there are pending/blocked funds.

## Appending a Transaction (openpyxl)
1. Find last data row and the `TOTALES` row.
2. `ws.insert_rows(totals_row)` — new row lands at the TOTALES position; TOTALES shifts down by one.
3. Write the entry in the new row (Fecha, Concepto, Entra/Sale, etc.). Keep the date-column convention of the sheet (this workflow leaves the time column blank for chat-sourced entries).
4. Fix the `TOTALES` SUM range to include the new row, e.g. `=SUM(D4:D13)` → `=SUM(D4:D14)`.
5. The running-balance column is a formula `=F(r-1)+D(r)-E(r)`; it recalculates on open.

## Verifying the Running Balance
- Don't trust `load_workbook(..., data_only=True)` immediately after a headless LibreOffice recalc — on some macOS setups the recalc is **not cached** into the file, so formula cells still read `None`.
- Verify by computing the balance in Python from the known prior-balance base plus the new movement(s): `saldo = base + sum(entra) - sum(sale)`. This confirms the row was entered correctly even when the file's cached formula value is unavailable.
- The formula is still correct for when the user opens the file in Excel.

## Cloud Push (Drive)
Token revocation is common. Use the console reauth flow (not a browser popup): generate the auth URL from the client_id with `redirect_uri=http://localhost`, have the user paste the returned code, then upload. See the `google-workspace` skill for the canonical setup; the key fix here is the **localhost redirect** (OOB is deprecated and returns `400 invalid_request`).

## Pitfalls
- **Balance vs transaction:** a fund screenshot is a balance → `referencia/fondos.json`, not a ledger row. Misclassifying inflates patrimonio.
- **Double counting:** if a fund's reported balance already embeds a transfer you also recorded as a movement, the total is wrong. The real bank balance wins; note the embedded component.
- **Ambiguous screenshot amounts:** always confirm the intended figure when two numbers sit at the same Y. Don't guess.
- **Headless recalc cache:** verify balances in Python, not via `data_only` post-convert.

## References
- `references/nu-screenshot-ocr.md` — worked tesseract TSV example disambiguating a Nu "arriendo apto 301 y 401" screenshot ($60.944,76 disponible vs $17.180,47 sibling).
