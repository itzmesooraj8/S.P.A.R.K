#!/usr/bin/env python3
"""
S.P.A.R.K. Secure Thin-Client
Designed for Termux / Mobile / Remote CLI control.
Signs requests using HMAC-SHA256 and sends them over a secure tunnel.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import urllib.error

def load_env_or_default(key: str, default: str = "") -> str:
    """Try to load a key from environment, or from a local .env file."""
    # Look in os.environ first
    if key in os.environ:
        return os.environ[key]

    # Look in a local .env if present
    if os.path.exists(".env"):
        with open(".env", "r", encoding="utf-8") as f:
            for line in f:
                if line.strip().startswith(key + "="):
                    return line.split("=", 1)[1].strip().strip('"\'')
    return default

def get_config() -> tuple[str, str]:
    """Retrieve SPARK URL and Secret Key."""
    url = load_env_or_default("SPARK_URL", "http://localhost:8000").rstrip("/")
    # Try SPARK_SECRET_KEY first, fall back to SPARK_TOKEN
    secret = load_env_or_default("SPARK_SECRET_KEY", load_env_or_default("SPARK_TOKEN", "change-this-token"))
    return url, secret

def record_audio_termux(filename: str, duration: int) -> bool:
    """Record audio using Termux API if available."""
    if not shutil.which("termux-microphone-record"):
        return False
    
    print(f"[*] Recording for {duration} seconds (Termux microphone)...")
    # Start recording
    subprocess.run(["termux-microphone-record", "-d", str(duration), "-f", "wav", filename], check=True)
    return os.path.exists(filename)

def record_audio_python(filename: str, duration: int) -> bool:
    """Record audio using sounddevice/scipy if installed."""
    try:
        import sounddevice as sd
        import scipy.io.wavfile as wavfile
        import numpy as np
    except ImportError:
        return False

    print(f"[*] Recording for {duration} seconds (Python sounddevice)...")
    sample_rate = 16000
    audio = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype="int16")
    sd.wait()
    wavfile.write(filename, sample_rate, audio)
    return True

def play_audio(filename: str):
    """Play audio file using available command-line tools."""
    # Try Termux media play
    if shutil.which("termux-media-player"):
        subprocess.run(["termux-media-player", "play", filename], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return
    
    # Try play (Sox)
    if shutil.which("play"):
        subprocess.run(["play", filename], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return

    # Try aplay (ALSA)
    if shutil.which("aplay"):
        subprocess.run(["aplay", filename], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return

    # Try ffplay (FFmpeg)
    if shutil.which("ffplay"):
        subprocess.run(["ffplay", "-nodisp", "-autoexit", filename], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return

    # Try standard open command (macOS / Windows / Linux desktop)
    try:
        if sys.platform == "darwin":
            subprocess.run(["open", filename])
        elif sys.platform == "win32":
            os.startfile(filename)
        else:
            subprocess.run(["xdg-open", filename])
    except Exception:
        print("[!] No supported audio player found. Audio saved to response.mp3.")

def send_command(url: str, secret_key: str, text: str | None = None, audio_path: str | None = None):
    """Signs and sends the command request to the remote home machine."""
    payload: dict[str, Any] = {
        "timestamp": time.time(),
    }

    if text:
        payload["text"] = text
    elif audio_path:
        with open(audio_path, "rb") as f:
            payload["audio"] = base64.b64encode(f.read()).decode("utf-8")
            payload["format"] = "wav"
    else:
        print("[!] Either text or audio must be provided.")
        return

    # Sign the canonical serialized payload
    serialized = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode("utf-8")
    signature = hmac.new(secret_key.encode("utf-8"), serialized, hashlib.sha256).hexdigest()

    request_data = json.dumps({
        "payload": payload,
        "signature": signature
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{url}/api/satellite/command",
        data=request_data,
        headers={"Content-Type": "application/json"}
    )

    print(f"[*] Sending request to S.P.A.R.K at {url}...")
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            
            # Print response text
            reply = res_data.get("reply")
            print(f"\n[SPARK] {reply}\n")
            
            if res_data.get("tool_used"):
                print(f"[*] Tool executed: {res_data.get('tool_used')}")
                if res_data.get("tool_result"):
                    print(f"[*] Output preview: {res_data.get('tool_result')[:120]}...")

            # Play audio response if returned
            audio_response = res_data.get("audio_response")
            if audio_response:
                audio_bytes = base64.b64decode(audio_response)
                out_filename = "response.mp3"
                with open(out_filename, "wb") as f:
                    f.write(audio_bytes)
                play_audio(out_filename)
                
    except urllib.error.HTTPError as e:
        try:
            err_body = e.read().decode("utf-8")
            print(f"[!] Server error {e.code}: {err_body}")
        except Exception:
            print(f"[!] Server HTTP Error {e.code}: {e.reason}")
    except urllib.error.URLError as e:
        print(f"[!] Network Connection Error: {e.reason}")
    except Exception as e:
        print(f"[!] Error: {e}")

def main():
    parser = argparse.ArgumentParser(description="SPARK Remote Secure Thin-Client")
    parser.add_argument("command", nargs="*", help="Direct text command to execute")
    parser.add_argument("--voice", "-v", action="store_true", help="Record voice prompt using mic")
    parser.add_argument("--duration", "-d", type=int, default=5, help="Voice recording duration (seconds)")
    
    args = parser.parse_args()
    url, secret = get_config()

    if secret == "change-this-token":
        print("[WARNING] Remote client using default secret token. Please set SPARK_SECRET_KEY or SPARK_TOKEN in .env or environment variables.")

    # 1. Voice Mode
    if args.voice:
        temp_wav = "temp_voice.wav"
        recorded = False
        
        # Try Termux microphone first
        if not recorded:
            recorded = record_audio_termux(temp_wav, args.duration)
            
        # Try Python sounddevice next
        if not recorded:
            recorded = record_audio_python(temp_wav, args.duration)
            
        if not recorded:
            print("[!] Could not record voice. termux-microphone-record not found, and sounddevice Python library not installed.")
            sys.exit(1)

        send_command(url, secret, audio_path=temp_wav)
        
        if os.path.exists(temp_wav):
            try:
                os.remove(temp_wav)
            except OSError:
                pass

    # 2. Command Arguments Mode
    elif args.command:
        prompt = " ".join(args.command)
        send_command(url, secret, text=prompt)

    # 3. Interactive CLI Mode
    else:
        print("=== SPARK Secure Remote Interactive Terminal ===")
        print("Type your prompt below. Enter 'exit' to quit, or '/voice' for a 5s voice command.")
        while True:
            try:
                prompt = input("spark> ").strip()
                if not prompt:
                    continue
                if prompt.lower() in ("exit", "quit"):
                    break
                if prompt.lower() == "/voice":
                    # Run voice command
                    temp_wav = "temp_voice.wav"
                    recorded = record_audio_termux(temp_wav, 5) or record_audio_python(temp_wav, 5)
                    if not recorded:
                        print("[!] Could not record voice.")
                        continue
                    send_command(url, secret, audio_path=temp_wav)
                    if os.path.exists(temp_wav):
                        os.remove(temp_wav)
                else:
                    send_command(url, secret, text=prompt)
            except KeyboardInterrupt:
                print("\nExiting interactive terminal.")
                break
            except Exception as e:
                print(f"[!] Error: {e}")

if __name__ == "__main__":
    main()
