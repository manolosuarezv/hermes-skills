# Hermes Skills

Skills de Hermes — procedimientos, recetas y convenciones de TU_NOMBRE.

## Estructura

```
<categoría>/<nombre-skill>/
  SKILL.md              # instruccin principal (frontmatter: name, description)
  references/           # documentación extendida por tema
  templates/            # plantillas reutilizables
  scripts/              # código ejecutable
  assets/               # archivos de apoyo
```

## Convenciones

- Cada `SKILL.md` lleva frontmatter YAML con `name` y `description`.
- La `description` es el **trigger**: describe *cuándo* usar el skill, no qué hace.
- Documentación larga va en `references/`, nunca inflada dentro de `SKILL.md`.
- Un skill = un procedimiento. Si necesitás dos, son dos skills.

## Versionado

- Git local en `~/.hermes/skills/` (historial completo de cambios).
- GitHub: `USUARIO_GITHUB/hermes-skills` (respaldo y revisión).
- Backup en Tritones (USB) y qbex vía `~/bin/backup-skills.sh`.

## Backup

```bash
~/bin/backup-skills.sh
```

Genera archive versionado por timestamp, commit al repo, copia a los tres destinos y verifica.

## Categorías

| Categoría | Contenido |
|---|---|
| autonomous-ai-agents | Conexión y orquestación de agentes |
| creative | Diagramas, mockups, generación de imagen |
| devops | Hermes, gateway, costos, SDLC |
| email | IMAP/SMTP, triage, AgentMail, bancos |
| github | Auth, PRs, issues, code review |
| homelab | qbex, Mac Mini, WOL, Docker, backups |
| mlops | Modelos, serving, evaluación |
| productivity | Contabilidad, Excel, documentos, OCR |
| research | Papers, RSS, citas, monitoreo |
| web | Recuperación de páginas bloqueadas |
