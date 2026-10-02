---
name: ledger-accounting
description: "xlsx ledger: entra/sale as stated; soporte is proof not move"
version: 1.0.0
author: Hermes (curator)
license: MIT
platforms: [macos, linux, windows]
---

# Ledger Accounting

Use when the user asks to create, update, or maintain an accounting / movement-register
workbook (Excel `.xlsx`) for personal or family bookkeeping.

## Established workbook structure — FOLLOW it, do NOT reinvent

The user already maintains canonical accounting workbooks. **Locate the existing file
before creating anything new** (see Workflow). The established format observed:

- One workbook per **ENTITY** (e.g. `contabilidad Renata suarez 2026.xlsx`,
  `contabilidad familia suarez 2026.xlsx`). Never mix entities in one file.
- Sheets: a `Resumen` sheet (per-month totals: `Mes | Entra | Sale | Saldo mes`) plus
  12 monthly sheets named `Enero 2026` … `Diciembre 2026`.
- Each monthly sheet columns: `Fecha | Hora | Concepto | Entra | Sale | Saldo | Soporte`.
  - `Saldo` is an **accumulated formula** (= prior saldo + Entra − Sale).
  - `Soporte` holds the receipt/support **reference** (text or number), NOT a money value.
- The `Resumen` totals feed from each month's Entra/Sale sums.

## Financial-statement workflow

When the user asks to organize cards, accounts, or financial products, maintain one worksheet per distinct product—not merely per institution—named exactly as the user specifies. Separate credit and debit/account products even when they belong to the same bank; separate investment products such as Fiducuenta, Fidurenta, and funds; and preserve the distinction between company and product (for example, related products can share a company without sharing a worksheet). Identify cards from statement messages and attachments using issuer plus last four digits; do not infer a product type from an incomplete snippet, a last-four number, or a guessed bank convention. Include statement date, covered period, due date, minimum/full payment when available, charge rows, source email/message ID, and an explicit unknown marker for fields absent from the email. Search Gmail with `in:anywhere`, including Spam and Trash, and report duplicate messages separately from unique statements. Read the exact message and attachment metadata before claiming a period or classifying a product; email snippets are discovery evidence, not sufficient financial evidence. If the user explicitly authorizes a worksheet but the evidence is incomplete, create only the clearly named empty worksheet and mark unresolved fields as unknown—do not invent movements or classification evidence.

### Statement attachments: encrypted PDFs that the mailbox deletes

1. **Pull statement attachments the day they arrive, not when the period is reviewed.** They land in the provider's Trash/Spam and are purged ~30 days after arrival; a later "reconcile last month" finds nothing. Search with `includeSpamTrash=True` (Gmail) / Spam+Trash included — a default search returns zero hits and reads like "no statements exist".
2. **The PDFs are password-protected; read them with `pypdf`.** `rd = PdfReader(path); rd.decrypt(key)` returns `1` or `2` on success (2 = owner password) — both mean readable, so assert `ret in (1, 2)`, and never treat 2 as failure. Keep the key in a local file (mode 600, listed in `.gitignore`), read it from the path, and never put it in chat, git, or a script.
3. **Archive the text layer beside the PDF:** `<name>.pdf` + `<name>.txt` + a `<sha256>  <relpath>` manifest. Then parsing, tests, and re-checks need neither the key nor the PDF after the mailbox purges the originals.
4. **Stage statements locally; supports go to the backup/RAID target only — never to the shared Drive folder.** Drive is for the live workbook; statements are custody evidence (link rot and wrong custody otherwise).
5. **Statement text extraction is lossy for tables.** Tabular statements (e.g. Nu) come back out of order, with literal mask/placeholder lines: parse by anchored labels (`Usado`, `Disponible`, `Total a pagar`, `Pago mínimo`, `Fecha límite`, `Valor Unidad`, `Rentabilidad Periodo`) and assert an identity such as `cupo = usado + disponible` before trusting the numbers.
6. **Alerts are the daily source; the statement is the monthly authority.** If the period's alert rows do not sum to the statement, write an explicit flagged row/state (`Descuadre — revisar`) and the difference — never silently adjust a row so the totals agree.

## Hard rules (from explicit user corrections)

1. **Separate files per entity.** Renata's books and Familia Suárez's books are different
   workbooks. Do NOT record a Familia Suárez movement (e.g. arriendo) into Renata's
   workbook even if the same people are involved.
2. **Register exactly as stated — entra como entra, sale como sale.** Put incoming
   amounts in `Entra`, outgoing in `Sale`, with no transformation or "cleanup".
3. **A "soporte" is PROOF of an existing movement, NEVER a separate movement.** If the
   user says a comprobante of X covers movements A + B (where A + B = X), record A and B
   as the real movements and put the comprobante reference in the `Soporte` column. Do NOT
   also add a row for X — that would duplicate the sum.
   - Worked correction: comprobante 210.000 = odontólogo 125.000 + pasajes 85.000.
     Real movements: −125.000 (odontólogo), −85.000 (pasajes). The 210.000 is soporte only.
8. **Classify confirmed account-to-account transfers as internal movements, not income or expense.** In a consolidated workbook where both sides must remain visible, show the same amount in `Entra` and `Sale` on the transfer row (or use the workbook's established paired-row convention) so the net balance is unchanged; never add the transfer to payroll or expense totals.
4. **Confirm before modifying.** Show the planned row(s) and get approval before writing
   to the workbook. The user reviews corrections first ("dime qué va a corregir y te
   apruebo"). For a clearly requested new worksheet or explicitly named card tab, the
   requested worksheet creation is approved; still verify the exact workbook and planned
   fields before writing.
5. **Familia Suárez workbook: day/month/year only, no hour.** The user explicitly does
   not want the `Hora` column filled for this entity — record only the day (the month is
   implied by the sheet). Leave `Hora` empty. (Renata's book may differ; follow whatever
   the existing file shows.)
6. **Derived "% of neto" movements are real Sales, but the target fund is a SEPARATE
   entity.** When the user says e.g. "sale el 10% del neto para fondo de mantenimiento",
   record it as a genuine `Sale` in the familia book (10% × the incoming net). The
   maintenance fund has its OWN balance tracked in a banking app — do NOT record that 10%
   back into the familia workbook as an `Entra`. Two distinct funds; keep them apart
   per rule 1.
7. **Verify computed balances against the user's screenshots.** The user often sends
   fund-balance screenshots from their banking app. OCR them locally to cross-check:
   `tesseract <img>.jpg stdout --psm 6 -l spa`. (vision_analyze / vision_analyze on a
   local path returns HTTP 404 on this macOS setup — use tesseract, not vision_analyze,
   for local images.) Confirm the workbook's `Saldo` matches the screenshot before
   reporting done.

   8. **Treat fund consolidation as a separately evidenced internal reallocation.** First list each source fund's balance, the amount moved from that source, the destination fund, and the resulting balance; keep Renata's funds separate unless the evidence explicitly includes them. Record the transfer only after the source and destination are identified, and never infer a consolidated total from a coincidentally equal payment, an opening balance, or a user's approximate figure.

   9. **Distinguish review drafts from approved accounting.** If the user explicitly asks for a Drive version to review, rows may be staged with a visible `PENDIENTE DE APROBACIÓN` status, but do not present them as definitive and do not hide unresolved source, destination, or support fields.

   ## Workflow

### Reconciling batches of banking screenshots before ledger edits

1. Recover the prior review context when the user asks to resume: search session history by the task title or distinctive domain terms, then read the last analysis and unresolved questions. Do not restart from the workbook or infer answers from the latest message alone.
2. Inventory the complete image batch and preserve order. For a large batch, create numbered contact sheets or OCR text files in batches; verify the discovered count against the user's stated count before extracting transactions. Count attachment objects programmatically from the source message and report that exact count; never infer the count from filename ranges or a truncated API response. If the source is a local archive, test the exact requested path first, then search the directory for case/spacing variants and inspect the archive with `unzip -l` before concluding that supports are present or absent. If the archive is on a Tailscale host, verify the exact remote path over SSH before searching local Downloads; use a read-only `stat`/`unzip -Z1` probe and stream only the needed text with `unzip -p` rather than copying the whole archive unnecessarily. Never request or accept the SSH password in chat. If the archive contains only `chat.txt`/`chat.md` and placeholders such as `<image omitted>`, report that the transcript records the support but the original images are not available for independent visual/OCR verification; do not claim to have inspected the images.
3. Extract each visible transaction with date, time, exact Cajita/fund label, counterparty/description, amount, direction, source image, and confidence. For long chronological histories, inspect adjacent screenshots around the target date and save a structured evidence table before reasoning from it. Use local OCR for banking screenshots when vision access is unavailable, and retain the source-image reference for every proposed row. For historical balance questions, distinguish explicitly between (a) a balance shown or reconstructed before withdrawals, (b) an identified withdrawal amount, and (c) an unproven total balance; never present an identified withdrawal as the fund's prior balance.
4. Reconstruct concentration events in two passes: first total only the explicitly visible Cajita withdrawals/deposits and list every contributor; then reconcile that subtotal to the later withdrawal or payment, labeling any residual as pre-existing or unresolved rather than assigning it to a fund by inference. Preserve the exact decimal arithmetic and show the residual calculation.
5. Classify before totaling: separate real economic movements from internal transfers between pockets/Cajitas, payment funding movements, duplicated screenshots, and movements belonging to another fund or entity. Never count an internal transfer as both income and expense.
5. Compare the proposed movements against both canonical workbooks and flag duplicates, contradictions, and missing context. Present a numbered decision list with the exact alternatives and amounts; do not modify either workbook while any ambiguity remains. When allocating a purchase funded by several pockets, preserve each amount only when the screenshots identify its source; do not force the full purchase total to equal an inferred three-fund split.
6. After the user confirms, show the planned rows grouped by workbook and month, then write only approved movements. Preserve the source screenshot as `Soporte` when appropriate; a screenshot or comprobante proves a movement and is not itself another movement.
7. Re-read both workbooks after writing and verify row placement, Entra/Sale direction, balances, and summary totals. Regenerate the read-only HTML viewer only from the verified workbook revision.

### When merging a local ledger into a Drive-backed unified workbook

1. **Verify Drive authentication before any Drive operation.** Run `setup.py --check` or test the token:
   ```bash
   TOKEN=$(python3 -c "import json; print(json.load(open('~/.hermes/google_token.json'))['token'])")
   curl -s -H "Authorization: Bearer $TOKEN" "https://www.googleapis.com/drive/v3/files?spaces=drive&fields=files(id,name)"
   ```
   If this returns 401/403, the token is invalid or revoked. Recover with `google-workspace` before proceeding:
   - If `google_token.json` is expired but has a `refresh_token`, refresh it.
   - If no valid token exists, recover from the old Drive token file (`~/.hermes/contabilidad/drive_token.json`) which often contains the embedded `client_id` and `client_secret` — use those to rebuild `google_client_secret.json` and re-auth. See `google-workspace/references/credential-recovery.md`.
   - **Never start a Drive merge with a revoked token** — the upload will fail silently or write to a different file.
2. **Check authentication and download the remote workbook before writing.** Run `setup.py --check`, then download the exact Drive file ID to a temporary path. Never overwrite or upload the local unified workbook before comparing the remote copy, because Drive may contain edits absent locally.
2. **Inventory all three inputs with bounded, machine-readable output:** the remote download, the local unified workbook, and the source entity workbook. Record sheet names, row counts, headers, and normalized movement rows (including dates as ISO strings). Compare by the canonical movement fields, not by workbook file hashes, because XLSX metadata and formula caches differ.
3. **Use the repository's canonical builder when it is the established merge path.** Run it only after preserving a backup of the current unified workbook; inspect its output and confirm that it retains unrelated entities (Renata, Trii, funds, summary, and log). If the builder's source set or behavior is unclear, stop before the Drive write and show the differences.
4. **Update the existing Drive file ID, not a new upload.** Use the Drive Files update/media-upload operation with the correct spreadsheet MIME type and preserve the canonical file ID. If the wrapper only exposes create/upload, stop before creating a duplicate and use the underlying update API or ask for confirmation; never trash the prior file as a cleanup shortcut. Treat the write as incomplete until a fresh download of that exact file ID is read back and its sheets, row counts, first-sheet summary, log, and last movement are verified.
5. **For a user-directed period close/open, update the first `Resumen` sheet before other operational changes.** Read the Drive source as the authority, preserve the detailed movement sheets unless the user explicitly approves edits, record closure/opening balances and new funds in the summary and change log, and keep unresolved historical reconstruction outside operational balances. Recalculate with LibreOffice, then verify the displayed cached values with `data_only=True`.
6. **Regenerate the HTML from the verified local unified workbook, then update the existing historical HTML file if that file is the intended review surface.** Restart or verify the Tailscale-bound viewer and test both loopback and the Tailscale URL; report the exact review URL. Keep HTML generation and Drive workbook update coordinated so the page does not describe a different workbook revision.

### Local-only workbook maintenance

1. **Find the existing workbook FIRST — never build from scratch.** Search, in order:
   - `~/bin/*.sh` and dotfile scripts — backup scripts often name the exact `.xlsx` path.
   - Local accounting dir (e.g. `~/.hermes/contabilidad/`).
   - iCloud Drive: `~/Library/Mobile Documents/com~apple~CloudDocs/`.
   - Google Drive only if truly needed (requires google-workspace OAuth; avoid forcing
     setup if the file is already local).
2. Open with `openpyxl`, read the target month sheet, append the new movement row(s) with
   a correct accumulated `Saldo` formula.
   - **Watch the TOTALES row.** Monthly sheets ship with a placeholder `TOTALES` row at the
     first empty line (e.g. row 4) containing `=SUM(D4:D3)`-style self-referential
     formulas. When you add data, write the movements ABOVE it and move the TOTALES row
     down (it must sit AFTER the last movement). Fix its SUM ranges to cover the real
     movement rows, and add an accumulated `Saldo` formula per movement row
     (`=prior_saldo - Sale + Entra`). A broken `=SUM(D4:D3)` returns 0 and silently
     zeroes the month.
   - **Keep `Entra`/`Sale` in columns D/E** even though the repo's `registrar.py` writes a
     legacy 3-column layout (`Fecha | Concepto | Monto` with negatives = sale). That script
     is OUT OF SYNC with the canonical 7-column workbook — do NOT use it; edit the workbook
     directly so the existing formulas/structure stay intact.
3. **Recalculate** so formulas show values (the bundled `xlsx/scripts/recalc.py` fails on
   Python 3.9, and openpyxl writes formulas with no cached value):
   `/Applications/LibreOffice.app/Contents/MacOS/soffice --headless --convert-to xlsx --calc --outdir /tmp/recalc_out file.xlsx`
   then reload with `data_only=True` to verify totals.
4. Verify: print the month sheet + Resumen totals; confirm `Saldo mes` matches the
   screenshot balance (rule 7). Also update the `Resumen` row for that month (Entra/Sale/Saldo
   mes) and the `TOTALES` row — the Resumen is NOT auto-linked by formula to the month sheet
   in the current workbooks, so it must be edited by hand.
5. Show the user the added rows; await approval before any further change.

## Pitfalls

- Resume requests require recovering the prior analysis and unresolved decision list first; starting from the workbook alone loses the image-batch evidence and the user's pending confirmations.
- For email-delivered evidence, use the provider REST API as the verification path when an MCP read returns a permissions error; validate the subject, thread, attachment count, and filenames before OCR. A successful listing does not prove every image was analyzed.
- Keep provider credentials out of notes and reports; retain only the mailbox address, endpoint pattern, and the fact that a configured credential is used.
- Creating a new workbook when one already exists → the canonical file is the source of
  truth; reuse its structure.
- Uploading before comparing the remote workbook → Drive may contain edits that are not
  present locally; download, normalize, compare, and back up first.
- Creating a second same-named Drive workbook or trashing the old one after a wrapper upload → links, permissions, and the user's canonical file ID can be lost; update the existing file ID and verify it by read-back.
- Updating detailed sheets before the first-sheet summary during a period close → the workbook can show operational data without the user's intended opening balances; update `Resumen` first and log the source and scope.
- Declaring a Drive update complete from the upload response alone → media uploads can
  succeed while the wrong file or revision is inspected; download the exact file ID and
  verify its sheets, first-sheet summary, and log after writing.
- Serving a stale HTML snapshot → regenerate from the verified unified workbook and test
  the viewer over both loopback and Tailscale before reporting the review URL.
- Treating a soporte amount as an extra movement → duplicates totals.
- Deduplicating alerts against manual rows on the exact date → duplicates every movement the provider notified after midnight (a purchase dated the 10th arrives as the 11th 00:01). Key on the provider message id AND on an economic key with ±1 day tolerance.
- Declaring a statement unreadable because extraction returns masked or shuffled lines → the figures are there under labelled anchors; look for the label before concluding the PDF is opaque.
- Mixing entities in one file.
- Leaving a movement "en ocasión" (pending) without a value → either get the value or
  omit it; don't leave placeholder rows that affect the saldo.
