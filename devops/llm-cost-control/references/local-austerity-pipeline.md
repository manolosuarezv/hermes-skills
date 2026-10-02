# Local-first token-austerity pipeline (recipe)

Reusable scaffolding for "routine = local Ollama $0, paid API gated behind a
recharge window + queue". Verified on a macOS finance bookkeeping setup.

## Files (drop into the project; mirror these)
- `referencia/estado_creditos.json` — credit state (presupuesto/usado/ventana/umbral).
- `scripts/control_creditos.py` — `estado|gastar|recarga|ventana|umbral`; exposes `hay_credito()`.
- `scripts/cola_claude.py` — `encolar|listar|completar|drenar`; `drenar` only acts if `hay_credito()`.
- `scripts/agente_local_asientos.py` — Ollama parser. Emits `RESULT_JSON <json>` marker on stdout so the orchestrator can capture the dict without re-parsing natural language.
- `scripts/registrar_git.py` — orchestrator: agente → registrar (xlsx) → build → anota CHANGELOG → commit.
- `scripts/drenar_cola_claude.sh` — wrapper for the $0 cron.
- `CHANGELOG.md` — append-only log; marker `<!-- REGISTRO MOVIMIENTOS -->` where automated lines insert.

## control_creditos.py core
```python
import json, os, datetime
PATH = "referencia/estado_creditos.json"
def cargar(): ...
def hay_credito():
    e = cargar()
    if not e.get("ventana_recarga"): return False
    pres, usado = e.get("presupuesto_claude",0), e.get("usado_claude",0)
    if pres <= 0: return False
    return (usado/pres) < e.get("umbral_ahorro", 0.8)
def recarga(m):  # sets ventana_recarga=True, ultima_recarga=today
    ...
```

## cola_claude.py core
```python
import json, os, sys, datetime
PATH = "referencia/cola_claude.jsonl"
sys.path.insert(0, os.path.dirname(__file__))
import control_creditos as cc
def drenar():
    if not cc.hay_credito():
        print("MODO AHORRO: sin ventana de recarga o sin crédito. Cola intacta.")
        return
    pend = [r for r in _leer() if r["estado"]=="pendiente"]
    for r in pend: print(f"  [{r['id']}] {r['desc']}")
    # mark 'notificada' so it isn't repeated until next encolar
```

## Ollama parse (strip the thinking block)
```python
import requests, json, re
def parse(texto):
    r = requests.post("http://localhost:11434/api/generate",
        json={"model":"qwen3:8b","prompt":SYSTEM+texto,"stream":False}, timeout=120)
    raw = r.json().get("response","")
    # qwen3 emits <thinking>...</think> then the answer; keep the tail
    if "</think>" in raw: raw = raw.split("</think>",1)[1]
    return json.loads(raw)  # {libro, tipo, monto, concepto}
```
Fallback: a regex `(\d[\d\.]*)`, keyword maps for libro/tipo when Ollama is down.

## $0 cron (no_agent=true, deliver=local)
```
schedule: every 6h
script:   drenar_cola_claude.sh   # cd project && ./venv/bin/python3 scripts/cola_claude.py drenar
no_agent: true
deliver:  local
```
In savings mode it's a no-op (no tokens, no delivery error). On recharge it
lists queued tasks so the user can "rendir la recarga" in the open window.

## Pitfalls
- The LLM returns data; deterministic code WRITES it. Never let Ollama/Claude
  mutate the xlsx directly.
- Capture the agent's output with a stable marker (`RESULT_JSON `), not by
  re-parsing human-readable stdout.
- git: exclude tokens/venv/backups (`drive_token.json`, `*.token.json`, `.env`,
  `venv/`, `*.bak*`, `*.pdf`). For private data prefer local-only git (no remote).
- CHANGELOG is append-only — corrections document, never delete.
- `cronjob create script=` MUST be a file under ~/.hermes/scripts/ (relative),
  not an absolute path — otherwise it's rejected. Put the wrapper there.
- Verify with a throwaway harness written to a `hermes-verify-*` temp file
  (write_file refuses /private/var/...; use the terminal heredoc instead),
  then delete it. Reset estado_creditos to 0 and restore any touched data
  files from a /tmp backup after the run.
