# Nu Screenshot OCR — worked example

Mobile banking screenshots (Nu app) pack several numbers at different vertical
positions. Plain `tesseract ... stdout` returns them in reading order, which
misassigns values to labels. Use the TSV with coordinates to map by position.

## Command
```bash
tesseract img.jpg stdout -l spa tsv 2>/dev/null \
  | awk -F'\t' '$12!="" {print $7, $8, $12}'   # left, top, text
```

## Real output (Nu "arriendo apto 301 y 401", 2026-08)
```
37 456 arriendo
173 460 apto
250 456 301
311 464 y
334 456 401
37 549 Total
38 578 $
64 582 60.944,76
38 673 Disponible
128 677 siempre
37 701 $        <- value left of "Disponible siempre" (top 701)
54 703 60.944,76
185 702 $       <- SECOND value, same row (top 702) = sibling figure
200 704 17.180,47
38 782 Invertido
178 782 CDT
37 810 $0,00
```

## Reading it
- `Total` (y≈549) = $60.944,76
- `Disponible siempre` (y≈673-701) left value = $60.944,76 → this is THE balance.
- At the SAME row (y≈702) there is a second value $17.180,47 to the right. It is a
  *different* figure — likely a sibling Cajita/account or a partial balance, NOT
  the disponible of the first one.
- `Invertido en CDT Nu` = $0,00. Rendimiento 9,30%–11,30%.

## Rule
When two numbers sit at the same Y (one left of the label, one to its right),
the RIGHT one is a separate balance. **Do not record it as the same account's
disponible.** Ask the user which figure is the intended balance before writing it
to `referencia/fondos.json` or a ledger. In this case the agent stopped and asked:
the $60.944,76 was the "arriendo 301 y 401" Nu balance; the $17.180,47 was left
unresolved pending user confirmation.

## Gotcha
Plain text mode gives no position, so `Total` and `Disponible` both reading
"$60.944,76" looked identical — only the TSV revealed the $17.180,47 sibling.
Always use TSV for fund screenshots.
