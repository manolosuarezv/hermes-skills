---
name: contabilidad-suarez-v2
description: Use when evolving Suárez accounting. Audit first.
---

# Contabilidad Suárez V2

Skill de clase para auditar, rediseñar y migrar el sistema contable Suárez sin perder datos ni trazabilidad.

## Reglas permanentes

- Trabaja en español, de forma directa y accionable.
- Antes de escribir, inspecciona los archivos, scripts, Git, libros y referencias reales.
- No edites libros, JSON canónico, Drive ni respaldos durante la auditoría de solo lectura.
- No inventes movimientos, saldos, entidades, soportes, IDs ni estados.
- Distingue hecho confirmado, derivado, hipótesis y pendiente.
- No borres fuentes ni respaldos; archiva y conserva hashes, logs y Git.
- No marques ni registres una propuesta ambigua sin aprobación explícita.
- Cada movimiento económico debe tener una entidad/producto, dirección, fuente y soporte identificables.
- Un soporte demuestra un movimiento; no crea otro movimiento.
- Las transferencias internas deben reflejar origen y destino cuando corresponda, sin convertirlas en ingreso o gasto económico.
- Cada movimiento se registra en la pestaña individual correspondiente; una transferencia interna no se duplica como dos movimientos dentro de la misma entidad/producto.
- Las salidas normales deben ser append-only; corrige errores con reversa referenciada, salvo duplicados o borradores confirmados y documentados.
- XLSX, HTML, Obsidian y Drive son salidas derivadas mientras no exista una decisión explícita y verificada que los convierta en fuente.

## Procedimiento obligatorio

1. Inventaría antes de diseñar:
   - `git status --short --branch` y `git log --oneline -12`.
   - Archivos, tamaños y rutas de `referencia/`, `scripts/`, `tests/`, soportes y backups.
   - Hojas, dimensiones, fórmulas y primeras filas de cada XLSX con `openpyxl` en modo lectura.
   - Dependencias y rutas de escritura de cada script con búsqueda de `save`, `json.dump`, `write_text`, aperturas en modo escritura y APIs de Drive.
2. Dibuja el flujo real, separando fuentes, transformadores, derivados, temporales e históricos.
3. Ejecuta comprobaciones sin escritura:
   - `./venv/bin/python3 -m compileall -q scripts tests`.
   - La suite de pruebas disponible en el proyecto, usando su intérprete y dependencias declaradas.
   - Comparación de hojas, movimientos, fórmulas, saldos, totales y hashes entre fuentes y derivados.
4. Identifica conflictos de autoridad. Si un script escribe XLSX y otro reconstruye ese XLSX desde JSON, detén la migración y resuelve primero cuál es la fuente canónica.
5. Define el modelo canónico mínimo: movimiento, fuente, evidencia, entidad, producto/cuenta, estado, ID estable/idempotente, aprobación, conciliación y eventos de auditoría.
6. Construye propuestas en modo dry-run; deduplica globalmente por identidad económica explicable, no por fecha y monto solamente.
7. Solicita aprobación para ambigüedades y para toda escritura real.
8. Escribe únicamente en la fuente canónica aprobada; genera XLSX/HTML/Obsidian desde ella.
9. Recalcula fórmulas con LibreOffice antes de leer valores con `data_only=True`; nunca guardes un libro cargado con `data_only=True`.
10. Verifica de nuevo la fuente, el derivado, el log, los saldos, los totales, los duplicados y los hashes. Si se usa Drive, actualiza el `fileId` canónico y descarga el mismo ID para verificarlo.
11. Cierra con backup verificable, estado Git y una explicación de cómo revertir.

## Arquitectura recomendada

- Mantén un núcleo local pequeño y auditable, inicialmente JSON append-only o SQLite; elige SQLite cuando las consultas, deduplicación y conciliación superen la complejidad razonable de JSON.
- Separa eventos de entrada y evidencias de los asientos económicos; varias fuentes pueden apuntar al mismo movimiento.
- Usa estados explícitos: `detectado`, `normalizado`, `pendiente`, `aprobado`, `registrado`, `conciliado`, `duplicado`, `excluido` y `revertido`.
- Usa Decimal o enteros de centavos para dinero.
- Haz que cada escritura sea idempotente, bloqueada y reversible.
- Mantén una CLI pequeña: `inventory`, `import`, `propose`, `approve`, `build`, `verify`, `sync`, `backup`.
- Conserva los libros antiguos como referencia de solo lectura hasta completar la reconciliación y la migración.

## Evaluación de software externo

Evalúa primero si la herramienta elimina complejidad real; no la adoptes por popularidad, documentación o comunidad.

- Odoo y ERPNext son opciones ERP de alta capacidad y alta complejidad: evaluar como exportación, conciliación o fase posterior, no como fuente canónica inicial.
- Akaunting y Firefly III pueden servir como interfaces o pruebas de finanzas, pero no sustituyen automáticamente el modelo de entidades, fondos, soportes y deduplicación.
- Beancount, hledger o Ledger son candidatos para una base auditable de texto plano, pero exigen decidir y migrar a doble partida.
- Para cada candidato registra: licencia, actividad del repositorio, instalación reproducible, importadores, localización colombiana/DIAN, backups, API, trazabilidad, coste de mantenimiento y posibilidad de reversión.
- Haz una prueba aislada con datos anonimizados antes de instalar o conectar un sistema externo al libro real.

## Formato de respuesta

Entrega, en este orden:

1. Estado actual.
2. Evidencia inspeccionada.
3. Fuentes de verdad y escritores reales.
4. Contradicciones y riesgos.
5. Propuesta mínima y alternativas descartadas.
6. Cambios o asientos propuestos, sin ejecutarlos si falta aprobación.
7. Pruebas ejecutadas y resultado.
8. Pendientes, aprobación requerida y reversión.

## Trampas conocidas

- No edites el XLSX derivado esperando que sobreviva al siguiente build.
- No mantengas dos escritores activos para la misma entidad sin una reconciliación explícita.
- No tomes el nombre de un archivo o una captura de saldo como prueba suficiente del movimiento.
- No confundas una transferencia entre entidades con ingreso o gasto.
- No declares sincronización de Drive por nombre de archivo: verifica ID, contenido y descarga de vuelta.
- No conviertas una auditoría parcial en una decisión de arquitectura; primero mide el flujo real y los escritores.
