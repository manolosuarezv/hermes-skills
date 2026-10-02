# Nous Portal model catalog — discovery & selection

When the user is on a Nous Portal OAuth subscription (not a paid API key),
the catalog of models their plan can call lives at Nous's inference API,
**not** in `hermes models` (which only lists providers whose key is set in
`~/.hermes/.env`). This file captures the discovery recipe + the model
families worth knowing for typical WhatsApp / vision / tool-calling tasks.

## Discovery recipe

```bash
TOKEN=$(grep NOUS_API ~/.hermes/.env | cut -d= -f2)
curl -s "https://inference-api.nousresearch.com/v1/models" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -c "
import json, sys
d = json.load(sys.stdin)
for m in d['data']:
    arch = m.get('architecture', {})
    mods = arch.get('input_modalities', [])
    has_vision = 'image' in mods
    print(f\"{m['id']:55s} ctx={m.get('context_length', '?'):>10}  vision={'Y' if has_vision else 'N'}  in={m.get('pricing',{}).get('prompt','?'):>10}  out={m.get('pricing',{}).get('completion','?'):>10}\")
"
```

The response is `{"data": [{"id", "context_length", "pricing": {"prompt", "completion"}, "architecture": {"input_modalities"}}, ...]}`.
`input_modalities` is the only reliable vision flag — `image` means the
model accepts images directly; absent means text-only (needs OCR upstream).

## Model families worth knowing
**Units — read this before quoting a price:** the `pricing.prompt` /
`pricing.completion` fields from `/v1/models` are per-token-scale (sub-cent)
numbers, NOT per-million. A raw value of `0.0002` corresponds to roughly
$0.16 per **million** tokens. Values shown below as "/M" are raw API fields
kept only so you can compare tiers — multiply before telling the user a price,
or quote the Portal models page.
The catalog is live and prices/promotions change. Do not preserve a dated
price table here or present a remembered model as currently available.
Fetch the exact model id, context, modalities, and pricing from the live
Nous endpoint and cross-check limits against the model owner's official docs
before making a comparison. The discovery recipe above is reusable; the
example families below are only selection hints, not availability claims.

- Prefer a vision-capable, tool-calling model for image-plus-action workflows.
- Prefer a fast/flash model for high-volume, cost-sensitive work.
- Treat a free Portal model as a catalog price, not as an unlimited quota.
- Treat model context length as unrelated to monthly subscription credits.


### Vision-capable, recommended for "look at receipt, run script"
- **`openai/gpt-5.6-luna`** — 1.05M ctx, $0.0002/M in · $0.0012/M out.
  Default recommendation for vision+tool-calling on Nous Portal.
- **`openai/gpt-5.6-luna:batch`** — same model, ~½ price. Use if the gateway
  supports batched dispatch (most don't; check first).
- **`z-ai/glm-5.3-flash`** — 1.31M ctx, $0.0001/M in · $0.0002/M out.
  Cheaper, vision, strong on structured-data extraction. Good
  cost-conscious pick.
- **`meta-llama/llama-4-scout`** — 1.31M ctx, $0.0001/M in · $0.0002/M out.
  Open-weights vision alternative.
- **`x-ai/grok-4.20`** — 2M ctx, $0.001/M in · $0.002/M out. The most
  capable vision+reasoning model on the catalog; reserve for hard cases.

### Free / near-free (good for high-volume fallback)
- **`deepseek/deepseek-v4-flash-0731`** — 1.31M ctx, **$0/M in · $0/M out**.
  Text-only — pair with local OCR (tesseract) when vision is needed.
  Strong fallback choice for cost-sensitive users.

### Pattern — paired primary + free fallback
For a WhatsApp accounting channel (receipt → script → log):
- Primary: a vision-capable cheap model (`z-ai/glm-5.3-flash` is the best
  cost/vision trade).
- Fallback: a free text model (`deepseek/deepseek-v4-flash-0731`) so
  follow-up questions and re-runs don't cost anything.
- Set via `hermes config set fallback_providers '[{...},{...}]'`.

## Pitfall — `hermes models` does NOT list the Portal subscription
A common first mistake: asking `hermes models` and concluding "no models
available." For OAuth users, the catalog above is the source of truth, not
`hermes models`. State this plainly so the user doesn't waste a round
looking for them in the wrong place.

## Pitfall — model id casing / version suffix matters
Model ids in the Nous Portal catalog are **case- and dash-sensitive**.
`DeepSeek-V4-Flash` ≠ `deepseek/deepseek-v4-flash-0731`. Always copy the
exact id from the discovery curl output, do not paraphrase.