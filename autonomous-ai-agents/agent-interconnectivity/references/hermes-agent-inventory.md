# Hermes agent inventory

Hermes no tiene un comando `hermes agents list`. "Agente" es un concepto difuso que se materializa de formas distintas. Para saber qué hay vivo ahora, consultar cada origen por separado.

## Orígenes de "agentes" vivos

| Qué quieres listar | Comando | Qué devuelve |
|---|---|---|
| Sesiones de chat (registros de conversación, incluyendo la actual) | `hermes sessions list` | Título, workspace, último activo, ID |
| Peers Hermes-to-Hermes (otros Hermes conectados) | `hermes peer list` | Lista de peers registrados o "No peers registered" |
| Tareas programadas (cron) | `hermes cron list` | Nombre, schedule, estado, última ejecución |
| Subagentes en ejecución ahora (lanzados vía delegate_task) | `delegate_task action=list` | Lista de hijos vivos con id, meta, estado |

Ninguno de estos es un inventario global de "agentes". Son ejecutores, sesiones, tareas y conexiones — dominios separados con comandos distintos.

## Lectura rápida de estado

```bash
# Sesiones
hermes sessions list

# Peers
hermes peer list

# Tareas programadas
hermes cron list

# Subagentes vivos (solo desde una sesión con delegate_task)
# (no hay comando CLI standalone; se consulta vía delegate_task action=list)
```

## Interpretación

- Si el usuario pregunta por "agentes" sin especificar, resolver ambigüedad antes de actuar: ¿sesiones? ¿peers? ¿cron? ¿subagentes?
- Un peer es un Hermes remoto registrado; un subagente es un proceso hijo efímero de delegate_task; una sesión es un registro de conversación; un cron es una tarea programada.
- No asumir que "orquentador" o "agente X" existe como entidad listable — verificar en los orígenes anteriores antes de afirmar que está o no.
