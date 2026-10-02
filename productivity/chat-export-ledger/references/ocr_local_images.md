# OCR de imágenes locales (fotos de export de chat)

`vision_analyze` NO puede leer rutas de archivo locales — devuelve `404 - Couldn't find that`
para paths como `/tmp/wachat/00000003-....jpg`. No reintentar en bucle; usar `tesseract`.

## Instalar (una sola vez)
```bash
# macOS
brew install tesseract tesseract-lang
# Linux (Debian/Ubuntu)
sudo apt install tesseract-ocr tesseract-ocr-spa
```

## Usar
```bash
# Siempre -l spa para capturas financieras en español
tesseract /tmp/wachat/00000003-PHOTO-2026-08-03-20-27-34.jpg stdout -l spa
```

## Campos a extraer de capturas bancarias (Nu / Bancolombia)
- Saldo **total** y **disponible** (líquido).
- "Por venir" / intereses próximos a disponible.
- Invertido en CDT (capital) y tasa %.
- Por cada CDT: vencimiento, tasa, capital, interés a la fecha, total.
- Comprobantes: monto, fecha/hora, origen→destino, estado, nº comprobante.

## Notas
- OCR puede confundir "S" con "$" y "N" con "M" en montos (p.ej. "N $4.171,92" = "+$4.171,92").
  Cruza con el total: suma de CDTs debe coincidir con "Invertido en CDT".
- Para lotes, iterar con un bucle shell sobre `*.jpg`.
