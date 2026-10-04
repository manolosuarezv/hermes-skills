# Safe audit checklist — comandos reales usados

Flujo aplicado en la auditoría del repo `~/.hermes/contabilidad/` (22 scripts +
4 crons). Reutilizable para cualquier repo personal del usuario.

## 1. Inventario (excluir venv)
```bash
cd <REPO>
find . -type f -not -path './venv/*' -not -path '*/__pycache__/*' | sort
echo "--- pesos ---"
wc -l scripts/*.py scripts/*.sh 2>/dev/null | sort -n
```

## 2. Docs del proyecto
Leer: CONTEXTO.md, PROTOCOLO*.md, README, CHANGELOG.md.
CUIDADO: suelen estar desactualizados vs la realidad (ej. PROTOCOLO decía Drive
"muerto" pero OAuth se rehabilitó después). Contrastar con crons + código.

## 3. Crons activos
```
cronjob action=list
```
Los crons dicen qué corre de verdad. En contabilidad: backup 00:00, cierre 23:30,
informe dominical (falló delivery), drenar_cola_claude cada 6h.

## 4. Mapeo de dependencias (CRÍTICO antes de borrar)
Los scripts NO se importan entre sí (cada uno independiente), pero los
orquestadores los invocan vía subprocess:
```bash
# grep de invocaciones (no solo imports)
search_files pattern='subprocess|runpy|os\.system'  file_glob='*.py'
search_files pattern='registrar|build_unificado|calc_trii|gen_vista|cierre_diario|digest_diario|cola_claude|backup_qbex|subir_drive|agente_local|control_creditos|reauth_drive|informe_semanal'  file_glob='*.py'
```
En contabilidad, los caminos reales:
- `registrar_git.py` → llama `agente_local_asientos.py`, `build_unificado.py`,
  `commit_contabilidad.sh` (vía bash) y anota CHANGELOG.md.
- `cierre_diario.py` → llama `digest_diario.py` + `backup_qbex.py`.
- `cola_claude.py` → `import control_creditos` (mismo dir).
- `informe_semanal.py` → `import registrar` (usa R.descargar/subir).

## 5. Clasificación aplicada (ejemplo contabilidad)
NÚCLEO (quedan): registrar, registrar_git, registrar_local, build_unificado,
cierre_diario, backup_qbex, commit_contabilidad.sh, agente_local_asientos,
digest_diario, cola_claude, control_creditos, gen_vista, calc_trii, subir_drive.

CANDIDATOS A _archive (limpieza histórica, ya cumplieron): fix_agosto,
corregir_dup_nomina, borrar_pruebas_enero, borrar_pagos_luz. Sus .bak_* ya están
en _archive/ → rollback posible.

DESHECHABLE/FUSIONAR: _lee_trii.py (inspección manual suelta, nadie lo llama).
DUPLICADO: gen_vista.py (114) vs gen_vista_completa.py (165) → unificar.
BORDE: reauth_drive.py, informe_semanal.py (revisar si el cron las usa).

## 6. Confirmar antes de borrar
El protocolo del usuario prohíbe borrar sin confirmar. Proponer plan A/B/C/D y
pedir visto bueno. Mover a _archive/ > rm.

## Hallazgo de eficiencia (la pregunta del usuario)
`build_unificado.py` lee `referencia/fondos.json` (saldos de fondos) que el
usuario EDITA A MANO. Eso es el cuello de botella: cada cambio en Drive exige
editar el JSON a mano. Mejora: sync Sheet de Drive → fondos.json automático vía
Sheets API + diff contra caché local (mostrar solo lo cambiado). Ver skill
google-workspace para la API.
