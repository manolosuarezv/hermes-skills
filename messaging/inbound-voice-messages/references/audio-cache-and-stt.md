# WhatsApp-on-macOS: inbound audio cache & STT discovery

Captured while diagnosing a real WhatsApp voice-note (`[ptt received]`) on a
freshly configured Hermes install on macOS. Context: no STT output was produced
because no working provider was wired up.

## What actually happened
1. Inbound voice note is NOT delivered as text. Hermes saved it as a file:
   `~/.hermes/cache/audio/aud_f4704c6bc2fe.ogg`
   `file` reported: `Ogg data, Opus audio, version 0.1, mono, 48000 Hz`.
2. `config.yaml` had `stt: model: whisper-1` (OpenAI cloud).
3. `grep -vE '^\s*#' ~/.hermes/.env | grep -iE 'OPENAI|GROQ|VOICE|WHISPER'`
   returned NOTHING — the key lines exist but are commented out with `#`.
   The capability banner claimed "Speech-to-text: active via Nous subscription",
   but there was no usable local key and no `faster-whisper` installed.
4. `ffmpeg` was NOT installed (`command not found`).
5. `python3 -c "import faster_whisper"` failed → local STT unavailable.
6. A direct `curl` to `https://api.openai.com/v1/audio/transcriptions` with
   `whisper-1` failed (no key extracted; key length 0).

## Hermes internals found (for deeper debugging)
- Transcribe endpoint served by the desktop/web server:
  `web_server.py` → `@app.post("/api/audio/transcribe")`, which calls
  `from tools.voice_mode import transcribe_recording` then runs it in an executor.
  Note: it expects a base64 `data:` URL, not a raw file path — so you can't
  trivially POST the cached file without wrapping it.
- `hermes_cli/voice.py` wraps `tools.voice_mode` (push-to-talk + continuous).
  `transcribe_recording` filters Whisper hallucinations.
- `config.yaml` STT key precedence documented in `.env` comments:
  `local > groq > openai > mistral > xai > elevenlabs`.
  Config comment: "Default STT provider is `local` (faster-whisper) — runs on
  your machine, no API key needed. Install with: pip install faster-whisper".

## Working fix paths (pick one)
- **Local / $0 (preferred for cost-conscious users):**
  `pip install faster-whisper`  +  `brew install ffmpeg` (or `port install ffmpeg`)
  then ensure `stt:` block does not force a cloud key.
- **Cloud OpenAI:** set an uncommented `VOICE_TOOLS_OPENAI_KEY=sk-...` in
  `.env` and keep `stt.model: whisper-1`.

## macOS permission-prompt clarification (given to user)
When terminal commands run on the user's Mac, macOS may show dialogs for
Files/Folders/Network/Microphone. Clarify:
- My commands were read-only `find`/`grep` + at most a `curl` network check.
- First run of the Hermes gateway touching `~/.hermes` is the likely prompt trigger.
- I never touched the mic/camera; inbound audio arrives as an already-saved file.
