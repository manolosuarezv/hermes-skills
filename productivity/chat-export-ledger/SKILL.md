---
name: chat-export-ledger
description: "WhatsApp export ZIP to formula-driven accounting Excel."
version: 1.0.0
author: Hermes Agent (curator)
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [WhatsApp, OCR, accounting, ledger, xlsx, finance]
    related_skills: [xlsx, ocr-and-documents]
---
# Chat Export → Accounting Ledger

Use when the user hands you a WhatsApp **group export** (a `.zip` containing `_chat.txt` and attached `*.jpg`/photos) and wants a financial register / Excel with a starting balance and recorded movements (e.g. "inicia cuenta con un saldo, registra los movimientos").

## When to use
- User sends `WhatsApp_Chat_-_*.zip` (or any chat export ZIP).
- They ask for an Excel/ledger of balances and movements from it.
- Recurring pattern for this user: "Presupuesto inventario y control" group → contabilidad de Renata.

## Pipeline (macOS / Linux)
1. **Extract** (unzip writes `_chat.txt` + photos):
   ```bash
   mkdir -p /tmp/wachat && unzip -o "<path>.zip" -d /tmp/wachat
   find /tmp/wachat -type f
   ```
2. **Read the transcript** with `read_file` on `_chat.txt`. Format:
   `[DD/MM/YY, HH:MM:SS] Name: message  <attached: 00000003-PHOTO-...jpg>`
   The `<attached: ...>` markers tell you which photos carry the numbers.
3. **OCR the attached photos** — see pitfall #1. Local `tesseract` is the reliable path.
4. **Build the Excel** with the `xlsx` skill (openpyxl): one "Resumen" sheet, one "Movimientos" sheet with a **running balance computed by formula**, and a "CDTs"/detail sheet if relevant. See `references/building_running_balance.md`.
5. **Recalculate** the formulas — see pitfall #2.

## Pitfalls
### 1. `vision_analyze` CANNOT read local file paths
It returns `404 - Couldn't find that` for absolute local paths like `/tmp/wachat/00000003-....jpg`. **Do not loop on it.** For local images use `tesseract` OCR instead:
```bash
brew install tesseract tesseract-lang   # macOS; apt on Linux
tesseract /tmp/wachat/00000003-PHOTO-....jpg stdout -l spa   # Spanish text
```
Photos are usually Spanish financial screenshots → always pass `-l spa`. Scan all 3 fields: total, disponible, and per-CDT rows. Full recipe in `references/ocr_local_images.md`.

### 2. `recalc.py` fails on Python 3.9
The xlsx skill's `scripts/recalc.py` calls `tempfile.TemporaryDirectory(..., ignore_cleanup_errors=...)`, which does not exist before Python 3.10 → `TypeError`. **Workaround: recalc via LibreOffice headless directly** (also works and rewrites in place):
```bash
/Applications/LibreOffice.app/Contents/MacOS/soffice --headless --convert-to xlsx --calc --outdir /tmp/recalc_out <file>.xlsx
```
Then verify cached values with `openpyxl.load_workbook(path, data_only=True)`. Need LibreOffice: `brew install libreoffice` (macOS). See `references/recalc_workaround.md`.

### 3. Movements with no amount in the chat
If the transcript records a movement without a value (e.g. "Sale de fondo para odontólogo de Renata" with no number), record it as a row but **do not debit the balance** — mark it with a `(*)` note so the user fills it in. Never invent an amount.

### 4. Running balance must be a formula, not a hardcoded number
Write `=F{prev}+D{row}-IF(ISBLANK(E{row}),0,E{row})` so the sheet recalculates. Hardcoding totals fails the xlsx skill's "zero formula errors / formulas not hardcoded" rule.

## Verification
- Recalculated file: load `data_only=True`, spot-check the final running balance and the SUM totals.
- Confirm CDT capital sum equals the "Invertido en CDT" figure from the Resumen (cross-check).
- `markitdown <file>.xlsx` to scan sheet names / headers.
