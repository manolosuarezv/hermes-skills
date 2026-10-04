# Purgar datos sensibles de un repo público de GitHub

Procedimiento para cuando la biblioteca de skills ya está publicada y se descubre que
contiene datos personales: ya no basta con editar el árbol, hay que reescribir el
historial completo y forzar el push.

## Cuándo dispara

- Un repo **público** contiene teléfono, correo, mailbox, IDs de Drive, nombre real,
  hostnames o usuario de GitHub embebidos en skills.
- Un escaneo encuentra el valor en `git log -p` aunque el árbol actual esté limpio.

## Principio

El **árbol** no es el riesgo: lo es el **historial**. Cada commit guarda el valor viejo
como línea `-` del diff, para siempre. Editar el archivo y commitear deja la cadena
completa expuesta para cualquiera que haga `git log -p` o clone --mirror. Solo la
reescritura de historial lo arregla.

## Procedimiento (una sola pasada)

```bash
REPO=<owner>/<repo>
FILTER=~/.hermes/hermes-agent/venv/bin/git-filter-repo   # pip install git-filter-repo

# 1. Clon MIRROR: trae todos los objetos, incluidos los inalcanzables
git clone --mirror https://github.com/$REPO.git /tmp/purge

# 2. Reglas LITERALES (sin regex) en un archivo aparte.
#    OJO: --replace-text NO interpreta regex. '\.' y '[a-z]' NO casan y pasan de largo.
#    OJO 2: este archivo es PUBLICO. Ejemplos con valores reales = nueva filtracion.
#    Usa siempre valores ficticios en la documentacion.
printf '%s\n' \
  '300123456789==>NUMERO_WHATSAPP' \
  'GMAIL_PERSONAL==>GMAIL_PERSONAL' \
  'agente@ejemplo.invalid==>agente@DOMINIO_MAILBOX' \
  'Mi-Mac.local==>HOSTNAME_MAC' \
  '1AbCdEfGhIjKlMnOpQrStUvWxYz01234==>ID_DRIVE_UNIFICADA' \
  'usuario-github==>USUARIO_GITHUB' > /tmp/rules.txt

# 3. Reescribir blobs de TODOS los refs
$FILTER --force --replace-text /tmp/rules.txt --replace-refs delete-no-add

# 4. Los metadatos de commit (Author/Email) NO los toca replace-text: filter-branch
git filter-branch --force --env-filter '
export GIT_AUTHOR_NAME="$(echo "$GIT_AUTHOR_NAME" | sed -e "s/^<nombre-real>$/USUARIO_GITHUB/")"
export GIT_COMMITTER_NAME="$GIT_AUTHOR_NAME"
case "$GIT_AUTHOR_EMAIL" in *@gmail.com|*@users.noreply.github.com|*@*.local) \
  export GIT_AUTHOR_EMAIL="EMAIL_GITHUB";; esac
export GIT_COMMITTER_EMAIL="$GIT_AUTHOR_EMAIL"
' --tag-name-filter cat -- --all

# 5. Borrar los refs de backup que filtro-branch deja (guardan el historial viejo)
git update-ref -d refs/original/refs/heads/main
git reflog expire --expire=now --all && git gc --prune=now -q

# 6. VERIFICAR ANTES DE PUSH, sobre todos los commits y blobs
# 7. Push forzado. El clon mirror hereda remote.origin.mirror=true: el push ignora
#    la rama y hay que desactivarlo o el comando falla en silencio.
git config --unset remote.origin.mirror   # o: remote set-url + push --force origin main:main
git push --force origin main:main
```

## Verificación obligatoria

Nunca digas "limpio" por el exit 0 del push. Recloná y escaneá **cada commit**:

```bash
git clone --mirror https://github.com/$REPO.git /tmp/verify
for c in $(git rev-list --all); do
  for f in $(git ls-tree -r --name-only $c); do
    git cat-file -p "$c:$f" | grep -c '<valor-real>' && echo "$c $f"
  done
done
```

También revisá `git log --all --format='%h %an <%ae>'`: los autores delata el origen.
Un `ghp_xx...xxxx` en documentación es un placeholder, no un token — pero
`gh[pousr]_[A-Za-z0-9]{20,}` también lo matchea. Confirmá leyendo la línea antes de
reportar una filtración.

## Pitfalls que costaron tiempo

- **`--replace-text` es literal, no regex.** Las reglas con `\.` o `[a-z]` no casan y
  el filtro reporta éxito con el leak intacto. Usá el valor exacto.
- **`git clone` normal no trae objetos inalcanzables.** Para auditar/purgar, usá
  `--mirror`.
- **`filter-branch` deja `refs/original/`.** Sin borrarla, un `git rev-list --all`
  sigue viendo el historial viejo y el escaneo cuenta los leaks dos veces.
- **`git-filter-repo` es one-shot por repo.** Una segunda corrida sin `--force` no
  hace nada, y los refs de la primera siguen ahí. Reseteá con `git reset --hard` +
  `git reflog expire` + `git gc` antes de reintentar.
- **El clon mirror tiene `remote.origin.mirror=true`.** Un `git push --force origin main`
  se ignora/falla con un remoto mirror. Desactivá la config antes de pushear.
- **Purgar y después commitear local reintroduce los leaks.** Si purgás y después
  creás un commit en el repo local (con tu nombre y host reales) y lo pusheás, la
  exposición vuelve. Secuencia correcta: primero aplicá los placeholders **en el
  working tree**, committeá, recién entonces purgá y pusheá.
- **Los placeholders rompen los comandos si no se documentan.** Si
  `<USUARIO_GITHUB>/hermes-skills` queda como default en un script instalado, el
  backup falla en silencio. Agregá un guard que detecte el placeholder y aborte.
- **No pases el valor real a un shell.** Usá la variable o armá la URL en Python
  para que un `<placeholder>` no se interprete como redirección de shell.

## Antes de publicar: checklist de datos

| Dato | Por qué importa |
|---|---|
| Teléfono / WhatsApp | Identificación directa + phishing |
| Correo personal | Identificación + spear-phishing |
| Mailbox de agente | Toma de cuentas del agente |
| IDs de Google Drive | Acceso DIRECTO al archivo, no solo referencia |
| Nombre real | Identificación |
| Hostname / `.local` | Topología + nombre de usuario implícito |
| Usuario de GitHub | Ya es público como dueño del repo, pero sustituirlo rompe URLs |
| OUID / org IDs | Identificación de la organización |
| Correos `noreply.github.com` | Tienen el ID numérico del usuario embebido |