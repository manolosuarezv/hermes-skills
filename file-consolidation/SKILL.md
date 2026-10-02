---
name: file-consolidation
description: Unificar varias copias de un archivo (local + Drive) en una versión canónica — comparar, snapshot, script, verificar, subir, commit.
version: 1.0.0
---

# Consolidación de múltiples copias de un archivo

Flujo para unificar varias versiones de un mismo archivo (local + Google Drive) en una versión canónica, documentada, reversible y sin corromper datos.

Uso: siempre que haya ≥2 copias de un `.xlsx` (o similar) dispersas entre disco local y Drive, y se necesite una versión unificada como referencia principal.

## Antes de empezar

1. **Inventariar todas las copias.** Locales + Drive. Anotar fecha, tamaño, número de hojas/campos.
2. **Descargar las copias de Drive** a un directorio local de respaldo (`_drive_backups/`), con nombres descriptivos (ej. `contabilidad_drive_18sep_1OA.xlsx`), no con timestamps aleatorios.
3. **No modificar nada aún.** Solo leer y comparar.

## Comparación

Usar `openpyxl` (Python) para comparar estructura y contenido:

- **Nivel 1:** listado de hojas, número de filas con datos por hoja, número de columnas.
- **Nivel 2:** comparación hoja por hoja del contenido (filas, celdas, valores).
- **Nivel 3 (si needed):** detalle movimiento por movimiento en las hojas de tarjetas/registros.

Documentar las diferencias en `LOG_TRAZABILIDAD.md` o archivo equivalente.

## Decidir la versión base

Criterios:
- **Completitud:** la copia con más hojas/datos suele ser la mejor base.
- **Formato:** si hay diferencias de estructura (formato expandido vs. compacto), preferir el formato más rico como base e incorporar solo lo único de las otras.
- **No aplicar como definitivos los movimientos pendientes de aprobación** — documentarlos, no materializarlos sin confirmación.

Tomar nota de la decisión y el motivo antes de tocar el archivo.

## Snapshot antes de modificar

```bash
mkdir -p "_snapshot_<descripcion>_<timestamp>/"
cp archivo_original.xlsx "_snapshot_.../archivo_original.xlsx"
cp otros_archivos_relevantes "_snapshot_.../"
```

El snapshot permite restaurar con `cp` si algo sale mal. Documentar la ruta del snapshot en el log.

## Script de consolidación

Escribir un script Python (`scripts/consolidar_<fecha>.py`) que:

1. Carga la versión base.
2. Incorpora las hojas únicas de las otras copias (copiando celda por celda, preservando estilos).
3. Añade/actualiza hojas de resumen y log de cambios.
4. Guarda el archivo unificado.

Ejecutar con ruta absoluta: `/usr/bin/python3 scripts/consolidar_<fecha>.py`

**No usar `python` — puede no existir; usar `python3`.**

## Limpieza de duplicados

Si el script o la edición manual dejó duplicados (ej. filas duplicadas en Resumen o Log de cambios):

- Escribir script de limpieza (`scripts/limpiar_duplicados_<fecha>.py`) **Y ejecutarlo**.
- O hacer la edición directa con openpyxl en el mismo paso.

**No escribir el script y no ejecutarlo** — eso deja los duplicados en el archivo final.

## Verificación

Después de consolidar:

1. Comparar hoja por hoja el archivo unificado con la base original para confirmar que no se corrompió nada.
2. Verificar que las hojas nuevas están presentes y con contenido.
3. Verificar que no hay duplicados en Log de cambios (contar timestamps únicos).
4. Verificar que las tarjetas/hojas de detalle conservaron su contenido.

## Subir a Drive

```bash
GAPI="python3 /ruta/a/google_api.py"
$GAPI drive upload "archivo_unificado.xlsx" --parent "ID_CARPETA_DRIVE"
```

**Importante:** `--folder-id` y `--update-id` **no son argumentos válidos** de `drive upload`. Usar `--parent FOLDER_ID`.

Verificar que el upload devolvió un ID nuevo y que el archivo en Drive tiene las hojas esperadas (descargar y comparar o usar `drive get`).

## Commit

```bash
git add -A
git commit -m "<descripcion>

- Base: <copia base> (motivo)
- Incorporado: <hojas/changes de otras copias>
- Pendientes: <movimientos sin aplicar>
- Snapshots: <ruta>
- Script: scripts/<nombre>.py"
```

No commitear archivos de credenciales (token.json, client_secret.json).

## `drive_links.txt`

Actualizar con:
- Enlace del archivo unificado en Drive (nuevo ID).
- Lista de versiones históricas (IDs antiguos) como referencia, no como enlaces activos principales.

---

## Pitfalls

- **Sin snapshot = sin reversibilidad.** El snapshot es obligatorio antes de modificar.
- **Script de limpieza escrito pero no ejecutado.** Deja duplicados en el archivo final. O se ejecuta o se hace manual.
- **Flags incorrectos en `drive upload`.** `--folder-id` y `--update-id` no existen. Usar `--parent`.
- **`python` vs `python3`.** En macOS, `python` puede no existir; usar `python3`.
- **Comparar sin antes descargar.** No se puede comparar contenido de Drive sin descargar a local primero.
- **Aplicar como definitivos movimientos pendientes de aprobación.** Documentar, no materializar sin confirmación externa.
- **Committing credenciales.** token.json y client_secret.json nunca van al repo.

---

## Referencias

- `scripts/consolidar_unificacion_20260926.py` — ejemplo de script de consolidación (hoja Fondo de auxilios + actualización Resumen + Log).
- `scripts/limpiar_duplicados_20260926.py` — ejemplo de script de limpieza.
- `LOG_TRAZABILIDAD.md` — formato de registro de trazabilidad (ver skill `suarez-contabilidad`).
