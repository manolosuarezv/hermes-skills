# macOS recalc pitfall + localized (es_CO) date parsing

## Pitfall: bundled `recalc.py` fails on macOS system Python (< 3.10)
`scripts/recalc.py` calls `tempfile.TemporaryDirectory(ignore_cleanup_errors=...)`.
`ignore_cleanup_errors` was added in **Python 3.10**. On macOS the system python is
often 3.9.x (e.g. 3.9.6), so the script dies with:

    TypeError: __init__() got an unexpected keyword argument 'ignore_cleanup_errors'

This is NOT a problem with your workbook — it is a Python-version incompatibility
in the bundled recalculation wrapper.

### Workaround: recalc via LibreOffice headless (soffice)
`soffice` is usually installed on macOS via `brew install libreoffice` and is on PATH
(`/opt/homebrew/bin/soffice`). Use it to compute every formula and cache the values:

    soffice --headless --calc \
      --convert-to xlsx:"Calc MS Excel 2007 XML" \
      --outdir /tmp /path/to/workbook.xlsx

THEN copy the recalculated file back to its real location:

    cp /tmp/workbook.xlsx /path/to/workbook.xlsx

**Do NOT set `--outdir` to the same directory as the source.** Overwriting the file
that soffice is reading fails with:
`SfxBaseModel::impl_store ... failed: 0x4c0c (Error Area:Sfx Class:Write Code:12)`
and the cached values are NOT written. Convert to `/tmp` (or any other dir) first,
verify, then copy back. Keep a `.bak*` of the original if anything goes wrong.

### Verify the recalc worked
After the copy-back, confirm the formula cached a real value:

    from openpyxl import load_workbook
    wb = load_workbook("/path/to/workbook.xlsx", data_only=True)
    print(wb["Sheet1"].cell(45,4).value)   # should be a number, not None

`data_only=True` on a file openpyxl just wrote (without recalc) returns `None`
everywhere — that is the tell that recalc did not happen. After soffice, it returns
the computed number.

## Parsing Spanish (es / es_CO) datetime strings from financial exports
Colombian exports (Trii, bank statements, Nequi, etc.) use formats like:

    "3 jun 2026, 7:11 p. m."
    "26 may 2022, 1:15 p. m."
    "21 feb 2025, 6:46 a. m."

Month is the 3-letter lowercase Spanish abbrev (ene, feb, mar, abr, may, jun, jul,
ago, sep, oct, nov, dic). Meridiem is "a. m." / "p. m." with internal spaces and
periods. p. m. adds 12h (except 12); a. m. 12 -> 0.

Reusable parser (stdlib only):

    import re, datetime
    MESES = {'ene':1,'feb':2,'mar':3,'abr':4,'may':5,'jun':6,'jul':7,
             'ago':8,'sep':9,'oct':10,'nov':11,'dic':12}
    rx = re.compile(r"(\d+)\s+([a-zñ]+)\s+(\d+),\s+(\d+):(\d+)\s+(a\. m\.|p\. m\.)")
    def parse_fecha(t):
        d, mes, a, h, mi, per = rx.search(t).groups()
        hh = int(h)
        if per == 'p. m.' and hh != 12: hh += 12
        elif per == 'a. m.' and hh == 12: hh = 0
        return datetime.datetime(int(a), MESES[mes], int(d), hh, int(mi))

Store the parsed `datetime` directly in the cell and set `.number_format =
"dd/mm/yyyy hh:mm"`. Decimals in values (e.g. 716771.74) survive untouched when cast
with `float()`.

## Applied example (session 2026-08-09)
Added an "acciones en trii" sheet to `contabilidad familia suarez 2026.xlsx` with 43
rows; TOTAL = `=SUM(D2:D44)` computed to 11.786.989,74 via the soffice workaround above.
