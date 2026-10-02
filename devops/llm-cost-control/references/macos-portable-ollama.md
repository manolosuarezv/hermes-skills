# Portable Ollama install on macOS — no Homebrew, no sudo

Used to give a cost-sensitive user a second local agent (Qwen) to offload work
from the main model. Observed on Apple M4 / 16 GB RAM, arm64.

## Why portable
`/usr/local/bin` is not writable without sudo; no Homebrew present. Ollama
ships a `.zip` with the binary inside `Ollama.app/Contents/Resources/ollama`.

## Steps
```bash
# download (180 MB) and extract into ~/.hermes/bin (no system writes)
cd ~/.hermes && mkdir -p bin
curl -sL -o /tmp/ollama.zip https://ollama.com/download/ollama-darwin.zip
cd ~/.hermes/bin && rm -rf ollama-darwin && unzip -q /tmp/ollama.zip -d ollama-darwin
OLL=~/.hermes/bin/ollama-darwin/Ollama.app/Contents/Resources/ollama

# start server in background
nohup $OLL serve > ~/.hermes/bin/ollama.log 2>&1 &
sleep 4
curl -s http://localhost:11434/api/version   # {"version":"0.32.5"}

# pull a model sized for 16 GB
$OLL pull qwen2.5:7b      # 4.7 GB quantized
```

## Benchmark on M4 / 16 GB
```bash
$OLL run qwen2.5:7b --verbose "Cuéntame un chiste corto en español."
# load 98ms | prompt eval 250 tok/s | eval 22.64 tok/s  -> fluid chat
```

## Constraints
- 16 GB RAM -> 7B is the sweet spot. 14B+ competes with Hermes/whisper/tts.
- Server does not auto-start after reboot. For persistence create a `launchd`
  plist (~/Library/LaunchAgents) that runs `ollama serve` on login.
- Qwen 7B is good but not equal to the `tencent/hy3:free` main model for
  general Spanish chat; best used as offload (summarize, classify, translate,
  clean text) to save main-model turns.

## Integrate with Hermes
Hermes can delegate to Ollama via `delegate_task` or by shelling out to
`$OLL run qwen2.5:7b "..."`. The OpenAI-compatible endpoint is at
`http://localhost:11434/v1`.
