---
name: ocr-local-images
description: "OCR local JPEG/PNG via tesseract when vision_analyze 404s."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [OCR, Images, Receipts, Banking, Vision-Fallback, Tesseract]
    related_skills: [ocr-and-documents, xlsx, suarez-contabilidad]
---

# Local Image OCR (tesseract fallback for vision_analyze 404s)

When a user sends a photo (WhatsApp, etc.) and `vision_analyze` returns
`404 - Couldn't find that`, do NOT keep retrying. First confirm the file is real,
then OCR it locally with `tesseract` — the binary reads local JPEG/PNG that the
vision pipeline fails to find.

## Step 0: Confirm the file exists (vision 404 is a false negative)

```bash
ls -la /Users/manuelsuarez/.hermes/cache/images/img_XXXX.jpg
file /Users/manuelsuarez/.hermes/cache/images/img_XXXX.jpg
# Expected: valid JPEG/PNG, e.g. "JPEG image data ... 413x1280"
```

If `file` reports a valid image but `vision_analyze` 404s repeatedly, the vision
router is misrouting a local path — this is a pipeline bug, not a missing image.
Do NOT treat it as "user didn't send a photo."

## Step 1: OCR with tesseract (no PIL needed)

```bash
# macOS: brew install tesseract  (already at /opt/homebrew/bin/tesseract)
# Linux:  apt install tesseract-ocr
TMP=$(mktemp -t ocr) && tesseract /path/to/img.jpg "$TMP" -l spa+eng && cat "$TMP.txt"
```

Verified working: read Colombian bank-transfer comprobantes (Nu -> Bancolombia),
including "$400.000,00" amounts and Spanish labels, with clean OCR.

## Step 2: Reading tips

- `-l spa+eng` for Colombian receipts / transfer proofs.
- No `PIL`/`pytesseract` import needed — call the `tesseract` binary directly
  from the terminal tool (avoids the missing-module rabbit hole).
- Multi-file: loop over paths, write each `.txt`, then read them.
- After OCR, the extracted text is the source of truth for downstream actions
  (e.g. recording a transaction amount) — note in your reply that the value
  came from OCR, not the vision tool.

## Pitfalls

- `vision_analyze` 404 != image missing. Always `file` the path first.
- Don't install `pillow`/python wrappers just to OCR — the CLI is enough.
- Numbers in receipts sometimes OCR with stray spaces (e.g. "$400. 000"); strip
  and parse to float before using as a money amount.

## Notes

- For PDFs/scans, see the `ocr-and-documents` skill (pymupdf, marker-pdf).
- For recording extracted amounts into accounting books, see `suarez-contabilidad`
  / `ledger-accounting` (Entra/Sale, Soporte column).
