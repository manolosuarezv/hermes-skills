# Modelo distinto solo para CLI (sin tocar los demás canales)

No existe una clave de config por plataforma para el modelo del CLI. La resolución real es:

- **CLI/TUI:** usa `model.default` (o `HERMES_MODEL`, o el flag `-m` del lanzamiento). No lee `platforms.<x>.channel_overrides` — eso es solo del gateway.
- **Gateway (WhatsApp, Telegram, etc.):** usa `platforms.<canal>.channel_overrides[<chat_id>].model`, y si no hay override cae al `model.default` global.
- **Cron:** el modelo por trabajo (`cron/jobs.json` → `model`/`provider`); si está vacío, usa `model_snapshot` (la foto al crearse) y si tampoco hay, el default global.

## Rutas para dejar DeepSeek (u otro) solo en el CLI

1. **Por lanzamiento (cero riesgo, sin reinicio):**
   ```bash
   hermes -m deepseek/deepseek-v4.1-flash
   hermes --tui -m deepseek/deepseek-v4.1-flash
   ```
   Verificado: responde en el modelo pedido sin alterar config ni gateway.

2. **Perfil aparte:** `hermes profile create <nombre>` y fijar `model.default` en ese perfil. Aísla modelo, pero también skills/memorias/cron — no sirve si se quiere conservar el contexto del perfil `default`.

3. **Default global:** `hermes config set model.default <modelo>`. **Efectos colaterales a revisar antes:**
   - Los canales del gateway sin `channel_overrides` (p. ej. WhatsApp) cambian de modelo.
   - Los cron jobs con `model` vacío y `model_snapshot` vacío pasan a fail-closed.
   - Requiere reiniciar el gateway, y ese reinicio no se puede hacer desde dentro de la propia sesión.

## Cambio en caliente (`/model`)

`/model <id>` dentro de una sesión cambia el modelo **solo de esa sesión**; al reiniciar o abrir una sesión nueva se vuelve al `model.default`. Sirve para probar "un tiempo" sin dejar rastro en config.
