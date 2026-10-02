# Cierre de sesión / backup general antes de apagar el Mac

Cuando el usuario anuncia que va a apagar el Mac mini y pide "no perder datos /
el camino por donde vamos / un backup general de este estado", ejecutar este
ritual COMPLETO. Es un procedimiento, no un paso opcional.

Orden obligatorio (cada paso depende del anterior):

## 1) Commit git del estado contable
El repo git ya existe en `/Users/manuelsuarez/.hermes/contabilidad/` (init en
sesiones previas). NO crear uno nuevo.

```bash
cd /Users/manuelsuarez/.hermes/contabilidad
git status --short
```

Si NO hay `.gitignore`, crearlo (ver plantilla abajo). Luego:
```bash
git add .gitignore CHANGELOG.md "contabilidad 2026.xlsx" \
  "contabilidad familia suarez 2026.xlsx" \
  scripts/<script_correccion>.py scripts/build_unificado.py \
  scripts/gen_vista.py scripts/gen_vista_completa.py \
  vista_contabilidad_2026.html vista_portafolio_trii.html "Rut 2026 actualizado.pdf"
git -c user.name="Hermenegildo" -c user.email="hermes@local" \
  commit -m "fix(contabilidad): <qué se corrigió y efecto en saldos>"
```
- Mensaje de commit: citar los 3 arreglos + efecto en patrimonio
  (p.ej. "Patrimonio 5.499.696,87 -> 4.719.732,87").
- NUNCA commitear `drive_token.json` (credencial OAuth). Dejar en `Untracked`
  o añadir a `.gitignore`.
- `Rut 2026 actualizado.pdf` y otros documentos del usuario: incluir para no
  perderlos.

## 2) .gitignore (plantilla)
Git es la BITÁCORA DE CAMBIOS, NO el repositorio de respaldos. Excluir lo
volátil para que el commit quede limpio y los `.bak` no ensucien el diff:
```
*.bak
*.bak_origen_*
.bak_portafolio_*
logs/
referencia/
__pycache__/
*.pyc
venv/
```
Verificar que funciona:
```bash
git status --short        # los .bak NO deben aparecer en el stage
git check-ignore contabilidad\ familia\ suarez\ 2026.xlsx.bak_origen_20260815_101838
# debe imprimir la ruta => está ignorado
```

## 3) tar de TODO el directorio (incluye respaldos que git excluyó)
El commit NO guarda los `.bak` ni logs. El tar SÍ (es el respaldo físico real).
```bash
cd /Users/manuelsuarez/.hermes/contabilidad
TS=$(date +%Y%m%d_%H%M%S)
DEST="backups/estado_general_${TS}.tar.gz"
mkdir -p backups
tar -czf "$DEST" --exclude='venv' --exclude='.git' --exclude='backups' \
  -C /Users/manuelsuarez/.hermes/contabilidad .
ls -lh "$DEST"
tar -tzf "$DEST" | head -30      # confirmar que incluye .bak y logs
```
El tar queda en `backups/` y SÍ contiene los `*.bak_origen_*` y `logs/` que
git ignoró. Tamaño típico ~550K (solo xlsx + scripts + html + pdf, sin venv).

## 4) Copia opcional al NAS
```bash
NAS="/Volumes/Nas"
if [ -d "$NAS" ]; then
  cp "$DEST" "$NAS/" && echo "COPIADO a NAS"
else
  echo "NAS NO montado (ignorable)"
fi
```
Si el NAS no está montado, el archivo local en `backups/` ya es suficiente.

## Notas de la sesión 15 AGO 2026 (ejemplo real)
- Commit `2cfb5e2` (14 archivos): corrige duplicado nómina (-929.964), borra 3
  filas de prueba (Enero) y 3 "sale pago luz" espurios (Agosto, 150.000).
- Patrimonio unificado: 5.499.696,87 -> 4.719.732,87.
- Tar: `backups/estado_general_20260815_101946.tar.gz` (553K).
- NAS no montado ese día => backup solo local; aceptable.
