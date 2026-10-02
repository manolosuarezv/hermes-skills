# WhatsApp → pipeline de contabilidad: diagnóstico y fix (18 AGO 2026)

## Síntomas reportados
- Usuario manda entradas por WhatsApp; los saldos NO se actualizan ("no me está llevando los saldos").
- El agente "parece fuera de contexto" al responder por WhatsApp.

## Arquitectura real (verificada, 18 AGO 2026)
- `bridge.js` (whatsapp-bridge) corre en el Mac mini, puerto 3000, modo self-chat, CONECTADO.
  - Ruta: `/Users/manuelsuarez/.hermes/hermes-agent/scripts/whatsapp-bridge/bridge.js`
  - Proceso: `node .../bridge.js --port 3000 --session /Users/manuelsuarez/.hermes/whatsapp/session --mode self-chat`
- El **gateway** corre como `python -m hermes_cli.main gateway run --replace` (PID distinto
  del bridge). Es ÉL quien hace GET a `http://127.0.0.1:3000/messages` y vacía la cola
  (`messageQueue.splice(0, len)`), entregando cada mensaje a la sesión del agente.
- Entrega cada mensaje a una **sesión del gateway propia de WhatsApp**
  (`agent:main:whatsapp:dm:NUMERO_WHATSAPP`), SEPARADA de la sesión CLI.
- El **session store** es la fuente de verdad de lo que dijo el usuario:
  `~/.hermes/sessions/sessions.json` (JSON dict; clave `agent:main:whatsapp:dm:NUMERO_WHATSAPP`
  → dict con `messages: [{role, content, ...}]`). Es CHICO (~3 KB), legible con python
  `json.load`, NO usar grep (revienta en timeout). Extraer mensajes `role=="user"` cuyo
  `content` empiece con `c:` para reproceso determinista SIN competir con el gateway.
- Esa sesión es la que debe cargar `suarez-contabilidad` y ejecutar `registrar_git.py`
  (agente local Ollama qwen3:8b → registrar_local → xlsx → build_unificado → commit git).
- El libro origen y el unificado se editan SOLO por ese pipeline determinista; el libro
  unificado es derivado (solo lectura de origen en build).

### IMPORTANTE: qué hoja edita el agente de WhatsApp
- El agente de WhatsApp (cuando sí actúa) registra en la hoja **Familia**
  (`contabilidad familia suarez 2026.xlsx`), NO en los fondos Nu bank.
- **Peligro comprobado (18 AGO):** si el agente mete la nómina ENTERA a Familia sin sacar
  la parte que va a Fondo, el patrimonio queda INFLADO. La nómina de JM (1.032.500) entra a
  Nequi → Nu bank (1.027.372 tras 4×1000=4.128 y dejar 1.000 en Nequi) y una porción va a
  Fondo de aptos / Fondo de emergencia (que viven en `referencia/fondos.json`, NO en el xlsx
  Familia). El saldo real de Familia 18 AGO = 61.901,2 (verificado intacto con openpyxl).
- Regla: NUNCA registrar una nómina completa en Familia sin la contrapartida de Fondo. Si no
  se sabe la asignación de fondo, ESPERAR aclaración del usuario, no inventar.

### Determinismo del disparador `c:` (no competir con el gateway)
- El gateway YA consume `/messages`. Un script propio que haga GET a `/messages` COMPITE y se
  queda sin cola. Por eso el reproceso determinista debe leer del **session store**
  (`sessions.json`), no del bridge.
- Flujo estable: usuario escribe `c: <texto>` en WhatsApp → el agente (skill cargado) O el
  cron de estabilización (leyendo `sessions.json`) invoca `registrar_git.py` con el texto.
  El cron es el respaldo cuando la sesión de WhatsApp perdió contexto (reset).
- `registrar_git.py` vive en `scripts/` del repo contabilidad; es el orquestador determinista
  (Ollama parse → xlsx → build_unificado → commit git). Invocarlo directo es más fiable que
  pedirle al LLM del gateway que lo haga.

## Diagnóstico paso a paso
1. `tail logs/contabilidad.log.jsonl` → fecha de la ÚLTIMA entrada.
   - Si es anterior a los reportes del usuario ⇒ el corte es enrutado, NO el libro.
2. Verificar salud del libro APARTE (no asumir que está roto):
   ```bash
   cd /Users/manuelsuarez/.hermes/contabilidad
   ./venv/bin/python3 - <<'PY'
   import openpyxl
   wb=openpyxl.load_workbook("contabilidad familia suarez 2026.xlsx", data_only=False)
   ws=wb["Agosto 2026"]
   for r in range(1, ws.max_row+1):
       v=[ws.cell(r,c).value for c in range(1,8)]
       if any(x is not None for x in v): print(r, v)
   PY
   ```
3. Probar el pipeline aislado:
   - `./venv/bin/python3 scripts/agente_local_asientos.py "hoy pago X 45000"` → debe dar BORRADOR.
   - `./venv/bin/python3 scripts/build_unificado.py` → debe reconstruir sin error y dar patrimonio.
4. Confirmar bridge conectado:
   - `ps aux | grep whatsapp-bridge/bridge.js`
   - `gateway_state.json` → `platforms.whatsapp.state == "connected"`.

## Fix estable (recomendado)
- Disparador determinista: el usuario escribe `c: <mensaje>` y eso invoca directo
  `registrar_git.py` (o un wrapper `whatsapp_inbound_contabilidad.sh`), SIN pasar por el
  LLM del gateway. Esto evita depender de que la sesión de WhatsApp cargue el skill ni de
  resets de sesión (que pierden contexto).
- Alternativa frágil: cargar `suarez-contabilidad` en autoload de la sesión WhatsApp
  (se pierde en reset de sesión → vuelve el fallo).

## Recuperar entradas perdidas
- Los mensajes del usuario que no llegaron NO están en `sessions/request_dump_*.json`:
  la sesión se resetea y el transcript reciente vive en memoria del gateway, no en disco.
- Pedir al usuario que reenvíe las entradas, o que dé su saldo REAL para conciliación
  inversa. NUNCA inventar movimientos ni saldos.

## Verificación post-fix
- Entrada de prueba `c: prueba 1` → debe aparecer en `logs/contabilidad.log.jsonl` + xlsx
  + unificado, ANTES de retomar entradas reales.
