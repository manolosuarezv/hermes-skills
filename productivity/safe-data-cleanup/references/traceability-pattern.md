# Patrón de trazabilidad (LOG + CONTEXTO)

Crear ESTOS DOS archivos en la raíz del repo antes de cualquier depuración.
Son la base de trazabilidad que el usuario exige (2026-08-19).

## LOG_TRAZABILIDAD.md — plantilla
Línea de tiempo cronológica de lo hecho y funcionado (verificado, no planeado).

```
# LOG DE TRAZABILIDAD — <repo>

## <AAAA-MM-DD> — <título del hito>
- Qué se hizo (acción concreta, ruta de archivo).
- Resultado verificado (commit hash, salida de comando).
- Por qué (motivo / mandato del usuario).
- Estado: COMPLETO | EN CURSO | PENDIENTE.

## <AAAA-MM-DD> — Cierre
- Resumen de archivos de trazabilidad.
- `git commit` final.
- NINGÚN dato fuente ni respaldo fue borrado; ubicación de _archive/.
```

## CONTEXTO.md — plantilla
Mapa unificado para cualquier canal (WhatsApp/Telegram/CLI/TUI).

```
# CONTEXTO UNIFICADO — <dominio>

## Estado actual (AAAA-MM-DD)
- Resumen de qué está funcionando.

## Arquitectura
- Repo / carpeta base: <ruta>
- Vault / destino legible: <ruta>
- Tokens/credenciales: <ruta, [REDACTED]>
- Skills relevantes: <nombre> (enabled)

## Reglas de trazabilidad (NO CORROMPER)
- Archivar > Borrar. Mover a `_archive/`.
- Cualquier estado pasado es reconstructible vía `git log` + LOG + _archive/.

## Cómo reconstruir la historia
1. `git log --oneline --all` en el repo.
2. `LOG_TRAZABILIDAD.md` → eventos de alto nivel.
3. Vault/datos fuente → estado por fecha.
4. `_archive/` → respaldos conservados.
```

## Convención de commits por paso
Un commit por paso reversible, mensaje con prefijo del paso:
`Fase B Paso1: ...`, `Fase B Paso2: ...`, `Fase B completa: ...`
Esto deja cada acción aislada y revertible individualmente.
