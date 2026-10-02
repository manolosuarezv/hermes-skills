---
name: safe-data-cleanup
description: Depurar datos sin borrar; archivar y preservar trazabilidad.
---

# Safe Data Cleanup (preservación + trazabilidad)

Cuando el usuario pida limpiar, depurar, unificar o refactorar archivos de datos
(suyos: libros contables, .xlsx, scripts .py, skills duplicados, vaults Obsidian),
NUNCA borrar. Mandato explícito del usuario (2026-08-19), innegociable:

> No corromper datos. En cualquier momento se debe poder reconstruir la historia.
> Archivar en vez de borrar. git como respaldo.

## Regla de oro
Archivar > Borrar. Mover a `_archive/` conserva el archivo íntegro y deja la raíz
limpia. El historial es reconstructible vía `git log` + `LOG_TRAZABILIDAD.md`
+ respaldos en `_archive/`.

## Secuencia (base de trazabilidad PRIMERO, luego plan, luego ejecutar)
1. **Antes de tocar nada**: crear `LOG_TRAZABILIDAD.md` (línea de tiempo de lo
   hecho/funcionado, verificado) y `CONTEXTO.md` (mapa de arquitectura + cómo
   reconstruir). Plantilla en `references/traceability-pattern.md`.
2. Proponer plan por pasos (un commit por paso) y esperar OK del usuario.
3. Ejecutar paso a paso, `git commit` tras cada paso reversible.
4. Nada se elimina: `.bak_*`, scripts obsoletos y skills duplicados → `_archive/`.

## Qué NO hacer
- `rm` / `git rm` sobre datos fuente o respaldos.
- Decidir solo qué mover cuando el script toca datos históricos (`fix_*.py`,
  `borrar_*.py`) — pedir pulso al usuario antes de moverlos.
- Hand-editar `~/.hermes/config.yaml` (ver Pitfall).

## Pitfall — NO forzar autoload de skill vía config.yaml
Si el objetivo es "que un skill funcione en todos los canales":
- NO uses `hermes config set platform_toolsets.<canal> "[...]"`. Esa clave es para
  **toolsets de plataforma** (hermes-cli, hermes-whatsapp…), NO para skills de
  usuario. `hermes config` la guarda pero advierte:
  `not a recognized config key — it was saved anyway, but Hermes may not read it`,
  y deja el YAML inconsistente (un canal como string, los demás como lista).
- El mecanismo oficial de skills-por-canal es `hermes skills config` (TUI
  interactiva, requiere sesión del usuario). No es automatizable desde el agente
  sin riesgo de romper el gateway.
- Si hay un skill DUPLICADO que compite en el skill-matching, archívalo — eso suele
  resolver "no funciona en todos los canales" sin tocar config.
- Si tocaste config.yaml por error: restaura desde respaldo (`cp config.yaml.bak_*`)
  y verifica con `hermes doctor`.

## Verificación al cerrar
- `git status` limpio tras cada commit.
- `hermes doctor` sin errores de config tras cualquier cambio en ~/.hermes.
- Raíz sin `.bak_*`; `_archive/` contiene lo movido.
