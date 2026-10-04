# Publicar la biblioteca de skills en GitHub

Los tres puntos donde esto se rompe, en orden de probabilidad.

## 1. `gh repo create` falla con "Resource not accessible by personal access token"

Causa: el PAT no tiene el scope `createRepository`, que viene dentro de `repo`.

Ojo con el mensaje: `gh` puede mostrar el error aunque el repo ya exista o el scope
esté bien. Antes de pedirle un token nuevo al usuario, **verificá el scope real por
HTTP**:

```bash
gh auth status
gh api scopes
gh api -i user 2>/dev/null | grep -i x-oauth-scopes
```

Si el header viene con los scopes esperados pero el comando sigue fallando, el
problema es la copia local de `gh` o un token cacheado en otro lado, no GitHub.

## 2. Classic vs fine-grained

- **Classic**: un solo campo "Select scopes" con checkboxes. `repo` da control total
  (públicos + privados). `public_repo` alcanza solo para publicar un repo público.
- **Fine-grained**: permisos por repositorio, hay que elegir el repo explícitamente
  y marcar "Administration: Read/Write" para poder crearlo.

Para este usuario, classic con `repo` es el camino más rápido y ya está configurado.
Si publicás solo repo público, `public_repo` alcanza y es más estrecho.

**Cuando Manuel tenga que crear o editar el token, mandale el link profundo de la
acción, no el de settings.** El URL con `?new` no siempre renderiza el formulario:

| Acción | Link |
|---|---|
| Crear token classic | `https://github.com/settings/tokens/new` |
| Editar un token | `https://github.com/settings/tokens` → fila del token → Edit |
| Registrar llave SSH | `https://github.com/settings/keys` |

Si la sesión del browser cae en un login wall, **parate y pedile que lo abra él**. No
intentes escribir la contraseña con las herramientas del browser.

## 3. `git push` da 403 aunque `gh` funcione

`gh` y `git` leen de almacenes distintos:

| Herramienta | Almacén |
|---|---|
| `gh` | `~/.config/gh/hosts.yml` |
| `git` (HTTPS) | `~/.git-credentials` o el helper configurado |

Cuando cambiás el PAT, actualizá los dos:

```bash
# 1. para gh
printf '%s' "$TOKEN" | gh auth login --with-token

# 2. para git push, sobreescribí la credencial del host
printf 'https://<user>:<TOKEN>@github.com\n' >> ~/.git-credentials
chmod 0600 ~/.git-credentials

# 3. si el repo local ya tiene el remote y otro remote configurado, chequeá cuál gana
git remote -v
```

Nunca imprimas el token en la salida, ni lo dejes en un archivo temporal sin borrar.
Si lo guardás para pasarlo, va a un archivo con `chmod 0600` que borras al terminar.

## Estructura del repo publicado

```
hermes-skills/
  README.md              # estructura, convenciones, versionado, categorías
  MANIFEST.json          # inventario generado
  <categoria>/
    <skill>/
      SKILL.md
      references/ templates/ scripts/ assets/
```

Solo `SKILL.md` es obligatorio; los archivos de apoyo son opcionales y se publican
junto a su skill.

## Qué excluir del repo

El repo es una copia **publicable**, así que fuera todo lo que es estado local o
privado:

```
.archive/       # backups de curator
.hub/           # índice/cache de skills instaladas
.curator_*      # locks y metadata de curator
.usage.json     # contadores de uso
._*             # AppleDouble
__pycache__/ *.pyc
```

`.git/` obviously no se copia — se usa `rsync --exclude='.git'` o `tar --exclude`.

## Verificación post-push (obligatoria)

```bash
gh api repos/<owner>/hermes-skills/git/trees/main?recursive=1 \
  --jq '[.tree[]|select(.path|endswith("SKILL.md"))]|length'
gh api repos/<owner>/hermes-skills/contents --jq '.[].name'
gh api repos/<owner>/hermes-skills/commits --jq '.[].commit.message'
```

El conteo de `SKILL.md` tiene que igualar el de `skills_list`. Si no, algo del
`.gitignore` o del `--exclude` se comió una categoría.