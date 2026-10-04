---
name: depurate-script-repo
description: "Audit and safely depurate a script project before deleting."
version: 1.0.0
author: Hermenegildo (Hermes)
license: MIT
---

# Depurar / auditar un repo de scripts personales

Cuando el usuario pide "revisar todos los scripts y depurar lo que no se necesite"
en una carpeta de proyecto, seguí este flujo ANTES de borrar nada. El objetivo es
NO romper el pipeline activo ni violar protocolos de no-borrado del usuario.

## Pasos (en orden)
1. **Inventariar** excluyendo el venv:
   `find . -type f -not -path './venv/*' -not -path '*/__pycache__/*' | sort`
   y pesos por script: `wc -l scripts/*.py scripts/*.sh | sort -n`
2. **Leer los docs del propio proyecto** (CONTEXTO.md, PROTOCOLO*.md, README)
   para entender arquitectura y qué scripts son "núcleo".
3. **Listar crons activos** (`cronjob action=list`) para saber qué corre de verdad
   por programación (no te fíes solo de los docs: suelen estar desactualizados).
4. **Mapear dependencias** entre scripts (para no borrar uno que otro invoca):
   - grep de imports: `import .*<nombre>`
   - grep de invocaciones: `subprocess|runpy|os.system` + nombre de script.
   - Un script que NADIE importa ni invoca y ningún cron usa = candidato a mover.
5. **Clasificar cada script** leyendo su docstring/header:
   - Núcleo (usado por crons o flujo diario) → se queda.
   - Limpieza histórica (`fix_*`, `borrar_*`, `corregir_*`) → ya cumplió su función;
     mover a `_archive/` si existe respaldo `.bak_*`.
   - Inspección manual suelta (`_lee_*.py`) → desechable o fusionar en su script padre.
   - Duplicados (`gen_vista.py` vs `gen_vista_completa.py`) → unificar en uno.
   - Utilidades de borde (`reauth_*`, `informe_*`) → confirmar si el cron las usa.
6. **Confirmar ANTES de borrar** (respetar protocolo de no-borrado del usuario).
   Proponer plan A/B/C/D y pedir visto bueno. Mover a `_archive/` es más seguro que `rm`.

## Pitfalls
- NUNCA borrar datos fuente ni respaldos; archivar en `_archive/`.
- Un script "muerto" puede ser llamado por un orquestador vía
  `subprocess.run([VENV, "scripts/X.py"])` — SIEMPRE grep de invocaciones, no solo imports.
- Los docs del proyecto suelen estar desactualizados (p.ej. PROTOCOLO decía Drive
  "muerto" pero se rehabilitó). Contrastar doc vs crons vs código real.
- Los scripts de limpieza histórica normalmente tienen respaldos `.bak_*` en
  `_archive/` → eso permite rollback, así que moverlos es seguro.
- Un script puede leer un JSON de referencia que el usuario EDITA A MANO (cuello de
  botella de eficiencia). Detectarlo abre la puerta a sincronizar desde la fuente
  real (p.ej. Google Sheet) en vez de edición manual — ver referencia.

## Verificación
Tras depurar: correr el orquestador principal (ej. `registrar_git.py`) y el build
para confirmar que nada se rompió.

## Referencia
- `references/safe_audit_checklist.md` — comandos y grep exactos usados en la auditoría.
