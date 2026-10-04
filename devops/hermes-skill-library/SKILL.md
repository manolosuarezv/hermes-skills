---
name: hermes-skill-library
description: "Version, document, back up and publish the skill library."
version: 1.0.0
author: Hermes Agent (session-derived)
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [skills, versioning, git, backup, github, manifest, documentation]
---

# Hermes skill library: versionar, documentar, respaldar, publicar

Clase de trabajo: dejar la biblioteca de skills de Hermes bajo control de versiones,
documentada, y respaldada en varios destinos. Se dispara con pedidos como
"¿le has hecho versiones a los skills?", "documenta los skills", "haz backup de los
skills a tritones/qbex/github", "sube los skills a GitHub".

NO es lo mismo que respaldar Hermes entero antes de un update (ver
`hermes-backup-and-update`): ahí el trigger es un update y el destino es un servidor
remoto. Aquí el trigger es la biblioteca de skills y puede tener varios destinos
(servidor, disco USB, GitHub), sin update de por medio.

## Cuando cargar
- Manuel pregunta por versiones, changelog, documentación o trazabilidad de los skills.
- Pide backup de skills a uno o varios destinos.
- Pide publicar/compartir la biblioteca de skills.
- Se cambia un skill de forma importante y hay que dejar registro.

## Reglas permanentes

- Resuelve el home activo con `$HERMES_HOME`; usa `~/.hermes` solo si no está definido.
  Nunca respaldes el perfil de otro agente por accidente.
- Los skills viven en `$HERMES_HOME/skills/`. El versionado es git **dentro de ese
  directorio**, no un repo aparte que copia: así el commit refleja el estado real.
- Separa la biblioteca de skills de Contabilidad y de cualquier backup de datos.
  Layout dedicado `<destino>/hermes/skills/`.
- Nunca muestres tokens, `.env` ni hashes de secretos. Reportá ruta, tamaño y
  verificación por destino.
- Un destino solo está "OK" si lo leíste de vuelta y comparaste tamaño o checksum.
  Un `cp`/`rsync`/`push` con exit 0 es éxito de transporte, nada más.
- Reportá en tabla: destino, estado, evidencia. Si un destino falla, decilo explícito
  y seguí con los demás; no declares éxito global.
- Cuando Manuel tenga que actuar en una UI web, **dale el link profundo de primera**,
  apuntando a la acción exacta. No lo mandes a navegar desde un URL genérico de
  settings.
- Responder en español, conciso: veredicto primero, después la tabla.

## Procedimiento

### 1. Inspeccionar el estado actual
```bash
skills_list                 # conteo autoritativo de skills
ls "$HERMES_HOME/skills"    # categorías y directorios ocultos
find "$HERMES_HOME/skills" -name SKILL.md | wc -l
du -sh "$HERMES_HOME/skills"
git -C "$HERMES_HOME/skills" status 2>&1 | head -3
```
Ese `git status` decide el flujo: si dice `not a git repository`, hay que inicializar.

### 2. Inicializar git en el directorio de skills
```bash
git -C "$HERMES_HOME/skills" init
```
Antes del primer commit crea `.gitignore` con el ruido de runtime:
```
.usage.json
.usage.json.lock
.curator_*
.archive/
._*
__pycache__/
*.pyc
```

### 3. Generar el manifiesto con un archivo, no inline
```bash
python3 "$HERMES_HOME/skills/devops/hermes-skill-library/scripts/gen_manifest.py"
```
Escribe `MANIFEST.json` con nombre, categoría, tamaño, mtime, sha256 del SKILL.md y
conteo de archivos de soporte por skill.

### 4. Escribir el README de la biblioteca
Debe cubrir: estructura de directorios (`SKILL.md` + `references/` + `templates/` +
`scripts/` + `assets/`), convenciones (frontmatter con `name`/`description`, la
description es el *trigger*, un skill = un procedimiento), cómo se versiona y cómo se
respalda, y una tabla de categorías con su contenido.

### 5. Commit local
```bash
git -C "$HERMES_HOME/skills" add -A
git -C "$HERMES_HOME/skills" commit -m "backup: <N> skills con documentacion y manifiesto"
```

### 6. Publicar en GitHub
Clona el repo destino, sincronizá la biblioteca con rsync, commit y push. Ojo con el
conflicto de credenciales `gh` vs `git` y con la verificación de scopes: ver
`references/github-publish.md` — es el paso que más falla.

```bash
gh repo create <owner>/hermes-skills --public --description "..."   # idem --private
git clone https://github.com/<owner>/hermes-skills.git /tmp/skills-push
rsync -a --exclude='.git' --exclude='.archive' --exclude='.hub' \
      --exclude='.curator_*' --exclude='__pycache__' --exclude='.venv' \
      --exclude='._*' --exclude='.usage.json*' \
      "$HERMES_HOME/skills/" /tmp/skills-push/
cd /tmp/skills-push && git add -A && git commit -m "..." && git push -u origin main
```

### 7. Copiar a disco USB / destino local montado
```bash
DEST=/Volumes/<disco>/backups/hermes/skills
mkdir -p "$DEST"
tar -czf /tmp/skills-$(date +%Y%m%d_%H%M%S).tar.gz \
    --exclude='.git' --exclude='.archive' --exclude='.hub' --exclude='.curator_*' \
    --exclude='__pycache__' --exclude='.venv' --exclude='._*' \
    --exclude='.usage.json*' -C "$HERMES_HOME/skills" .
cp /tmp/skills-*.tar.gz "$DEST"/; cp MANIFEST.json "$DEST"/; cp CHANGELOG.txt "$DEST"/
find "$DEST" -name '._*' -delete
shasum -a 256 /tmp/skills-*.tar.gz "$DEST"/skills-*.tar.gz   # deben coincidir
```
Verificá montaje antes (`mountpoint -q /Volumes/<disco>`); si no está, reportá
"NO MONTADO" y seguí.

### 8. Destino remoto (servidor homelab)
Verificá alcanzabilidad primero; si el server está apagado y es un homelab con WOL,
mandá el magic packet y **poll** hasta que responda antes de intentar rsync — ver
`homelab/homelab-wake-on-lan` para el flujo WOL→espera→ssh. Después rsync con
opciones batch y timeout acotado, y verificá leyendo el path remoto.

### 9. Reporte
Tabla destino/estado/evidencia + qué quedó pendiente. Si un destino no se pudo
completar, decilo con la razón y qué haría falta.

## Pitfalls

- **Nunca escribas Python inline con `python3 -c` en un `terminal()` para generar
  archivos.** Las comillas anidadas y los f-strings se rompen en 2–3 capas y
  producen `SyntaxError`; peor, un fallo a medias puede crear un archivo basura con
  contenido parcial en el cwd. Escribí el script con `write_file` y ejecutalo.
- **`gh` y `git` usan almacenes de credenciales distintos.** `gh` guarda en
  `~/.config/gh/hosts.yml`, `git` en `~/.git-credentials`. Corregir el scope del
  token en `gh` hace que `gh repo create` funcione mientras `git push` sigue
  dando 403 con el token viejo cacheado. Actualizá ambos.
- **Verificá scopes por header HTTP, no por `gh auth status` solo.** El truth es
  `gh api -i user | grep -i x-oauth-scopes`; un `Token scopes: none` puede venir de
  una copia local de `gh` aunque GitHub ya tenga el scope.
- **Los archivos `.json` validados no aceptan comentarios.** Un `#` de encabezado en
  `MANIFEST.json` hace que `write_file` rechace el archivo. Poné la nota en un campo
  del JSON o en el README.
- **Excluí `._*` (AppleDouble).** macOS los crea al copiar a discos no nativos
  (exFAT/USB) y ensucian el backup y el repo. Borralos tras cada copia.
- **Para borrar de git un archivo con nombre raro, usa `git ls-files -z`.** `git
  ls-files` entrecomilla los nombres con `\n` o comillas y el pathspec no matchea;
  con `-z` obtenes el nombre crudo y `git rm -- <path>` funciona.
- **El conteo de skills depende de cómo lo midas — declará el método.** `skills_list`
  cuenta skills *registrados*; `find -name SKILL.md` cuenta *archivos*, y difieren
  cuando hay directorios anidados, `_archive/` o el mismo skill duplicado en varias
  categorías. Antes de reportar "N skills", fijate cuál es el número honesto y decilo
  con su método ("71 skills registrados / 71 SKILL.md publicados"). Si no cierran, es
  bug de conteo, no un dato: investigá antes de publicar una cifra.
- **`skill_view` con nombre ambiguo se niega a adivinar.** Si el mismo nombre existe en
  dos rutas (skill suelto en la raíz y otro dentro de una categoría), llamalo por ruta
  categorizada: `skill_view(name='homelab/homelab-wake-on-lan')`. No reintentes con el
  nombre pelado. La colisión en sí se le reporta al usuario para que renombre.
- **Un `.tar.gz` con `--exclude` sobre `.git` no es historial.** Si el destino es
  disco local, preferí también el repo git; el tar es para transporte.
- **`git commit` con nada staged no es error**, es no-op: reportá "sin cambios desde
  último commit", no como fallo.
- **qbex (192.168.1.69) no despierta por WOL desde S5 frío.** `~/bin/prender-server.py`
  envía los magic packets y responde OK, pero el equipo no levanta ni por LAN ni por
  Tailscale (esperado: 90s de poll, 0 respuestas). Es comportamiento conocido del
  homelab, no una falla del script: reportá "qbex apagado — WOL no effective en S5
  frío, requiere encendido manual" y seguí con los demás destinos. No reintentes en
  bucle; dos intentos y reporte.
- **No declares éxito de GitHub por el exit 0 del push.** Verificá contra la API:
  `gh api repos/<owner>/<repo>/git/trees/main?recursive=1` y contá los `SKILL.md`.

## Archivos de apoyo
- `references/github-publish.md` — token classic vs fine-grained, verificación de
  scopes, el split `gh`/`git`, layout del repo, verificación post-push.
- `templates/backup-skills.sh` — script completo de los 3 destinos, parametrizable
  por env. Instalado en `~/bin/backup-skills.sh` con `GH_REPO` ya fijado a
  `USUARIO_GITHUB/hermes-skills`. Uso: `backup-skills.sh [git usb remote]`;
  probado y verificado (checksum USB OK, RESULT OK).
- `scripts/gen_manifest.py` — genera `MANIFEST.json`; corrélo, no lo reescribas.
