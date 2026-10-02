---
name: inbound-voice-messages
description: Transcribe voice notes from Hermes messaging channels.
---

# Inbound Voice Messages on Hermes Gateways

## When to load
- A user sends a voice note / PTT / audio clip to a Hermes channel (WhatsApp observed in practice) and you must understand its content.
- A user asks "can you hear / listen to my messages?" — verify by actually transcribing an inbound audio file, not by asserting capability.
- STT / transcription is failing or appears misconfigured on a Hermes install.

## How inbound audio arrives (key fact)
On the gateway, received voice media is **saved to disk as a file** — it is NOT streamed to you as text. For WhatsApp the file lands at:
`~/.hermes/cache/audio/aud_<hash>.ogg`  (Ogg/Opus, mono, 48 kHz).
Find the freshest one:
`find ~/.hermes -type f \( -name '*.ogg' -o -name '*.opus' -o -name '*.mp3' -o -name '*.wav' -o -name '*.m4a' \) -mmin -30`

## Transcription provider chain
`config.yaml` `stt:` block governs this. Provider priority (per Hermes docs):
`local (faster-whisper) > groq > openai > mistral > xai > elevenlabs`.
- `stt.model` may default to `whisper-1` (OpenAI cloud) even when no key is present — verify the key actually exists in `.env` (uncommented) before relying on it.
- Keys live in `~/.hermes/.env`. A line prefixed with `#` is INACTIVE.
- Local path needs `faster-whisper` + `ffmpeg` on PATH. **No Homebrew / no ffmpeg system install?** `pip install faster-whisper static-ffmpeg` — `static-ffmpeg` fetches a portable ffmpeg binary (e.g. `<venv>/lib/python3.11/site-packages/static_ffmpeg/bin/darwin_arm64/ffmpeg`). Prepend that dir to `PATH` before importing faster-whisper. Missing either → local STT silently unavailable.
- **Config is agent-write-protected**: you cannot `patch`/`write_file` `~/.hermes/config.yaml` (Hermes refuses). Switch providers with `hermes config set stt.provider local` (and `stt.use_gateway false` for `--force` if unrecognized). Do NOT try to edit config.yaml directly via tools.

## Direct transcription that works (no gateway dependency)
When `stt.provider: local` is set, you can transcribe the saved file directly without the web endpoint:
```python
import os
os.environ["PATH"] = "<venv>/lib/python3.11/site-packages/static_ffmpeg/bin/darwin_arm64:" + os.environ.get("PATH","")
from faster_whisper import WhisperModel
m = WhisperModel("base", device="cpu", compute_type="int8")
segs, info = m.transcribe(path, language="es", beam_size=5)
text = "".join(s.text for s in segs)
```
Pass the audio path as a `sys.argv` (not an inline var) so heredoc shells don't choke on `os.environ` lookups. `base` model transcribes ~7s Spanish audio in ~0.5s on an M4.

## Verification recipe
1. Confirm the file exists (find command above).
2. Inspect STT config: `grep -A3 '^stt:' ~/.hermes/config.yaml`
3. Check for an ACTIVE key: `grep -vE '^\s*#' ~/.hermes/.env | grep -iE 'OPENAI|GROQ|VOICE|WHISPER'`
4. If no key + no local engine: install local with `pip install faster-whisper static-ffmpeg` (no Homebrew needed) or set `VOICE_TOOLS_OPENAI_KEY` and keep `stt.model: whisper-1`. To enable local: `hermes config set stt.provider local` + `hermes config set stt.use_gateway false --force`.

## Outbound voice replies (local TTS) — the other half
When the user wants you to *send* a voice message (e.g. "mándame el mensaje de voz mejor"), generate audio and deliver it as a file. Prefer a **$0, non-Nous-pool** path:
- Set `hermes config set tts.provider edge` and `hermes config set tts.use_gateway false --force`.
  - `edge` = Microsoft Edge TTS (neural voices, **no API key, no cost, does NOT drain the Nous free tool pool**). For a 100%-offline alternative use `piper` (lower quality, but zero network) — install via `pip install piper-tts`.
- Install: `pip install edge-tts` (inside the Hermes venv).
- Pick a voice: `python -c "import asyncio,edge_tts; vs=asyncio.run(edge_tts.list_voices()); [print(v['ShortName'],v['Locale'],v['Gender']) for v in vs if v['Locale'].startswith('es-')]"` → female latam examples: `es-MX-DaliaNeural`, `es-CO-SalomeNeural`, `es-AR-ElenaNeural`, `es-PE-CamilaNeural`. Set with `hermes config set tts.voice es-MX-DaliaNeural --force`.
- **async gotcha**: `edge_tts.Communicate(...).stream()` is an async generator. You MUST wrap the call in `async def main(): ...` + `asyncio.run(main())`. A bare `async for` at module top level raises `SyntaxError: 'async for' outside async function`.
- Deliver via the platform's native attachment (e.g. WhatsApp: `MEDIA:/path/to/file.mp3`).

```python
import asyncio, edge_tts
async def main():
    c = edge_tts.Communicate("Texto en español.", "es-MX-DaliaNeural")
    with open("/tmp/reply.mp3", "wb") as f:
        async for ch in c.stream():
            if ch["type"] == "audio":
                f.write(ch["data"])
asyncio.run(main())
```

## Pitfalls
- **Banner vs reality**: the gateway may report "Speech-to-text: active via Nous subscription" while the local `config.yaml` still points to a cloud provider with no key. Trust the local config + an actual key-presence check, not the capability banner.
- **Commented keys are not set**: a key line with a leading `#` does nothing; don't assume a key exists just because the line is present.
- **Don't claim you "heard" it**: only state you transcribed it after producing real output from the file. Be explicit about failures (e.g. "no key, local engine absent").
- **macOS permission prompts**: running terminal commands on the user's Mac can make macOS show the user dialogs (Files/Folders, Microphone, etc.). If they ask "did you request these?" — clarify your commands were read-only file searches + at most a network check, and that the first run of the Hermes gateway touching `~/.hermes` is the likely trigger. You never attempted to use the mic/camera; inbound audio arrives as a saved file.
  - Also: a broad `find / -maxdepth 6 ...` triggers macOS "Files & Folders" prompts for Drive/Fotos/Music because the interpreter process touches those paths. Restrict scans to `~/.hermes` unless the user explicitly wants a whole-disk search.
- **Cost-conscious users**: prefer local `faster-whisper` ($0) for STT and `edge` TTS (free, off-Nous-pool) over cloud providers — aligns with their spend-control preference. Keep `image_gen`/`web`/`browser` on the gateway only if quality matters; each image/web call drains the free tool pool.
- **TTS async wrapper**: never call `edge_tts` stream at top level — wrap in `async def` + `asyncio.run`.

## References
- `references/audio-cache-and-stt.md` — concrete discovery transcript for a WhatsApp-on-macOS setup (paths, commands tried, gotchas).
- `references/local-tts-edge.md` — edge-tts setup, voice list, and the async-for pitfall with a runnable snippet.
