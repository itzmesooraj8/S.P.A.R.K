# S.P.A.R.K
**Sentient Proactive Autonomous Response Kernel**
> Personal AI assistant. Runs locally. Actually intelligent.

[![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-cyan)]()

Then open http://localhost:8000

## Public Access
SPARK can be exposed securely through a Cloudflare Tunnel or a VPS with HTTPS.

Recommended remote-access setup:
1. Set a strong `SPARK_ACCESS_TOKEN` in `.env`.
2. Keep `SPARK_ENABLE_TUNNEL=1` only after the token is set.
3. Point Cloudflare Tunnel at the local FastAPI server on `http://localhost:8000`.
4. Replace the placeholder hostname in `cloudflared-config.yml` with your real domain, or use a tunnel token.
5. Access the public URL over HTTPS and send `Authorization: Bearer <SPARK_ACCESS_TOKEN>` for protected routes.

Protected routes include `/chat`, `/listen`, `/voice-chat`, `/status`, `/api/status`, and `/hud`.
The login flow returns the currently configured bearer token so the HUD or client can reuse the same secret.

For a step-by-step launch guide, see [docs/DEPLOYMENT_CHECKLIST.md](docs/DEPLOYMENT_CHECKLIST.md).
For a live smoke test against your public URL, use [scripts/check_public_tunnel.py](scripts/check_public_tunnel.py).

## Architecture
```text
User Input (Voice/Text) → Whisper STT → Orchestrator → Groq LLM
                                                      ↓
                                               Tool Selection
                                    ┌──────────────┼──────────────┐
                                  Search      Weather/News     System
                                  Network       Browser          IoT
                                                  ↓
                                            ChromaDB Memory
                                                  ↓
                                        EdgeTTS → HUD WebSocket
```

## Features
- `web_search`: live internet lookup for current information.
- `get_system_stats`: CPU, RAM, disk, and system telemetry.
- `get_clipboard`: read the current clipboard contents.
- `open_url` and `open_app`: launch websites, maps, and desktop apps.
- `get_news`: fetch current headlines for a topic.
- `get_weather`: geocoded weather lookup through Open-Meteo.
- `get_network_connections`: inspect active network sessions and listening sockets.
- `control_device` and `list_devices`: MQTT-based home device control.
- `scene_leaving`, `scene_arriving`, `scene_good_night`: scripted home scenes.
- `read_screen` and `read_region`: OCR-based screen awareness.
- `listen_and_transcribe`: microphone capture plus Whisper transcription.
- `speak`: local text-to-speech output.
- Memory-backed recall with ChromaDB and categorized fact extraction.

## .env Setup
Copy `.env.example` to `.env` and fill in the variables below.

```env
GROQ_API_KEY=your_groq_api_key_here
SPARK_TOKEN=change-this-to-something-strong-32chars
SPARK_ACCESS_TOKEN=change-this-to-a-strong-secret
MQTT_HOST=192.168.1.100
MQTT_PORT=1883
NEWS_API_KEY=optional_newsapi_key
```

If both `SPARK_ACCESS_TOKEN` and `SPARK_TOKEN` are set, the API uses `SPARK_ACCESS_TOKEN` first.


## Run
Install dependencies, set up the environment, and launch the backend with your normal local start command. The HUD is served from the FastAPI app at `http://localhost:8000`.

## Notes
The repository keeps the current React HUD and FastAPI backend layout, while the phase prompts act as the functional specification for the assistant stack.

## Cloudflare Tunnel Setup

```bash
# Install cloudflared
wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb

# Authenticate
cloudflared tunnel login

# Create and run tunnel
cloudflared tunnel create spark-home
cloudflared tunnel run spark-home
```

For Windows and long-term remote access, the repository includes `start_spark.ps1`, which launches the API and then starts Cloudflared if a valid tunnel configuration or token is present.

If you use the named tunnel config, update `cloudflared-config.yml` so the hostname matches a real DNS record in Cloudflare.

Systemd service for auto-start on boot:

```ini
[Unit]
Description=SPARK Cloudflare Tunnel
After=network.target

[Service]
ExecStart=/usr/local/bin/cloudflared tunnel run spark-home
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

## OCR Setup (Screen Awareness)
To enable the `read_screen` functionality, install Tesseract OCR on your host machine:
- **Linux**: `sudo apt install tesseract-ocr`
- **Windows**: Install from [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki)
- **macOS**: `brew install tesseract`

After system install, ensure Python dependencies are available:
`pip install pillow pytesseract`

## Wake Word Setup
To enable the background "Hey SPARK" wake word engine:
```bash
pip install openwakeword
# If pyaudio fails on Windows, install it via pipwin:
pip install pipwin
pipwin install pyaudio
```
