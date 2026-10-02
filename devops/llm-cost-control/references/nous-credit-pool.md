# Nous credit/recharge mechanics (condensed)

User question observed: "¿cómo funciona la recarga de token con Nous? ¿cada
cuánto tiempo está?" — i.e. how the Nous paid credit pool renews.

## Key facts
- **Nous Portal = OAuth**, not an API key the user manages. The user "carga"
  credits (e.g. $5) into a Nous account; Hermes draws from that managed pool.
  There is NO provider-console limit the user sets for Nous — the cap is the
  account balance they funded.
- **Two separate cost surfaces under Nous:**
  1. **LLM conversation** — when on the default `tencent/hy3:free` model via
     Nous Portal, chat is $0 *per se*, but it rides Nous's **shared credit/rate
     pool**, not a limitless free tier. When that pool is exhausted the free
     model stops answering until renewal. This is what "se acabaron los tokens"
     means in practice for the free model.
  2. **Managed tools (free-tool pool, finite credits):** web search/extract
     (Firecrawl), browser automation, image generation (FAL/FLUX), STT/TTS via
     gateway. These DO draw the funded pool even while chat is "free".
- **Paid model choice is per-session:** the user can opt to spend their Nous
  balance on a stronger model. That spend draws the same funded pool.
- **Renewal timing:** there is no fixed public cadence the agent should assert.
  Tell the user: the free-model shared pool replenishes on Nous's schedule
  (don't invent a number); their *funded* balance only changes when they top
  it up. Check balance at https://portal.nousresearch.com or `hermes status`.
- **Austerity move:** keep routine work on a local Ollama fallback so a drained
  Nous free pool never blocks the workflow (see local-austerity-pipeline.md).

## What to tell the user
- "Cargaste $5 a Nous" → that's your funded balance; it only goes down when you
  use paid models or managed tools. The 'free' chat model pulls from a separate
  shared pool that Nous refills on its own cycle — if it cuts off, fall back to
  local Ollama to keep working at $0.
- Route STT/TTS local (faster-whisper / edge-tts) to avoid drawing the tool
  pool for voice; warn before image generation (largest drain).
