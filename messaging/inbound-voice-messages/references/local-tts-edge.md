# Local outbound TTS with edge-tts (Hermes venv, $0, off-Nous-pool)

## Why
User wanted voice replies ("mándame el mensaje de voz mejor") but cost-conscious —must not drain the Nous free tool pool. `edge` (Microsoft Edge TTS) is free, keyless, high-quality neural, and does NOT hit the pool. `piper` is the 100%-offline alternative (lower quality).

## Setup (one-time)
Inside the Hermes venv:
```
pip install edge-tts
hermes config set tts.provider edge
hermes config set tts.use_gateway false --force
hermes config set tts.voice es-MX-DaliaNeural --force   # female latam
```

## List available voices (filter by locale)
```python
import asyncio, edge_tts
async def main():
    vs = await edge_tts.list_voices()
    for v in vs:
        if v["Locale"].startswith("es-") and "Neural" in v["ShortName"] and v["Gender"]=="Female":
            print(v["ShortName"], v["Locale"], v["Gender"])
asyncio.run(main())
```
Female latam picks: es-MX-DaliaNeural, es-CO-SalomeNeural, es-AR-ElenaNeural,
es-CL-CatalinaNeural, es-PE-CamilaNeural, es-VE-PaolaNeural, es-US-PalomaNeural.

## Generate audio (RUNNABLE)
```python
import asyncio, edge_tts
async def main():
    c = edge_tts.Communicate("Texto en espanol.", "es-MX-DaliaNeural")
    with open("/tmp/reply.mp3", "wb") as f:
        async for ch in c.stream():
            if ch["type"] == "audio":
                f.write(ch["data"])
asyncio.run(main())
```
Deliver with MEDIA:/tmp/reply.mp3 (WhatsApp attaches it as audio).

## Pitfall — async for at top level
edge_tts.Communicate(...).stream() is an async generator. A bare async for at
module scope raises SyntaxError: 'async for' outside async function. Always wrap
in async def main(): ...; asyncio.run(main()).

## Switching to fully offline (piper)
```
pip install piper-tts
hermes config set tts.provider piper --force
```
Voices must be downloaded once (piper model card). Use when zero network egress is required.
