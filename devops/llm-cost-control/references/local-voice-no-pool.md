# Local voice I/O to save the Nous free tool pool

Reproducible recipe used on a Mac mini (Apple M4, arm64, no Homebrew, no sudo).
Hermes venv at `~/.hermes/hermes-agent/venv`; venv python/pip at
`~/.hermes/hermes-agent/venv/bin/python` (alias `$HM`).

## 1. STT — read the user's voice notes locally (faster-whisper)
```bash
HM=~/.hermes/hermes-agent/venv/bin
$HM/pip install faster-whisper static-ffmpeg
# static-ffmpeg fetches a portable ffmpeg binary — no system ffmpeg needed
```
Config (use `hermes config set`, NOT direct file edit — see main skill pitfall):
```bash
hermes config set stt.provider local
hermes config set stt.use_gateway false
```
`config.yaml` then shows `stt.local.model: base` (good balance).

Verify against a saved WhatsApp note (.ogg/Opus):
```python
import os
os.environ["PATH"] = "/Users/manuelsuarez/.hermes/hermes-agent/venv/lib/python3.11/site-packages/static_ffmpeg/bin/darwin_arm64:" + os.environ.get("PATH","")
from faster_whisper import WhisperModel
m = WhisperModel("base", device="cpu", compute_type="int8")
segs, info = m.transcribe(PATH, language="es", beam_size=5)
for s in segs: print(s.text, end="")
```
Result observed: 7s audio transcribed in 0.5s, 100% local, $0. WhatsApp voice
notes land in `~/.hermes/cache/audio/aud_*.ogg`.

## 2. TTS — agent's voice out, free, no pool draw (edge-tts)
```bash
$HM/pip install edge-tts
hermes config set tts.provider edge
hermes config set tts.use_gateway false
hermes config set tts.voice es-ES-AlvaroNeural   # --force if unrecognized
```
Test:
```python
import asyncio, edge_tts
async def main():
    c = edge_tts.Communicate("Hola, soy Hermenegildo.", "es-ES-AlvaroNeural")
    with open("/tmp/t.mp3","wb") as f:
        async for ch in c.stream():
            if ch["type"]=="audio": f.write(ch["data"])
asyncio.run(main())
```
`edge_tts` = Microsoft Edge neural voices, free, no API key. Alternative `piper`
is fully offline but slightly more robotic.

## 3. Re-pin a bumped transitive dep after pip install
`pip` may bump `packaging` (Hermes needs 26.0). After any venv install:
```bash
$HM/pip install "packaging==26.0"
$HM/python -c "import hermes_cli; print('ok')"   # confirm Hermes still imports
```

## Keep image/web/browser on the gateway for quality
Do NOT move `image_gen` to a local provider (SD-local < FLUX quality). Leave:
```yaml
image_gen:
  use_gateway: true
web:
  backend: firecrawl
  use_gateway: true
```
But warn the user before generating an image — it is the largest pool drain.
