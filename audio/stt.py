import speech_recognition as sr
import whisper
import warnings
import logging
import numpy as np

warnings.filterwarnings("ignore")
logger = logging.getLogger("SPARK_STT")

class SparkEars:
    def __init__(self):
        # UPGRADE: Switching to 'small.en' for significantly better accuracy on accented English.
        # Ryzen 5 5500U handles this model in ~1-1.5s per utterance.
        logger.info("Initializing S.P.A.R.K. Ears (Whisper Small - Enhanced Accuracy)...")
        self.model = whisper.load_model("small.en")
        self.recognizer = sr.Recognizer()
        
        self.recognizer.dynamic_energy_threshold = False
        self.recognizer.pause_threshold = 1.2 
        
        # Baseline threshold to block environmental noise
        self.base_threshold = 350 
        
        try:
            with sr.Microphone(sample_rate=16000) as source:
                logger.info("🎤 CALIBRATING MICROPHONE... Please remain silent.")
                self.recognizer.adjust_for_ambient_noise(source, duration=2)
                # Sensitive but grounded threshold
                self.recognizer.energy_threshold = max(self.base_threshold, self.recognizer.energy_threshold + 100)
                logger.info(f"✅ Calibration complete. Threshold: {self.recognizer.energy_threshold:.2f}")
        except Exception as e:
            logger.error(f"Calibration failed: {e}")

    def _process_audio(self, audio):
        """Processes audio with enhanced confidence gating."""
        audio_data = np.frombuffer(audio.get_raw_data(), np.int16).flatten().astype(np.float32) / 32768.0
        
        # Context primer to guide Whisper
        primer = "S.P.A.R.K. command mode. YouTube, time, applications, clipboard, screenshot, typing."
        
        result = self.model.transcribe(
            audio_data, 
            fp16=False, 
            language="en",
            initial_prompt=primer,
            condition_on_previous_text=False
        )
        
        text = result["text"].strip()
        text_lower = text.lower()
        
        # --- ENHANCED CONFIDENCE GATE ---
        segments = result.get("segments", [])
        if segments:
            # Average no_speech probability across segments
            avg_no_speech_prob = sum(s.get("no_speech_prob", 0) for s in segments) / len(segments)
            # Whisper Small is more confident; 0.4 is a safe cutoff for noise
            if avg_no_speech_prob > 0.4:
                logger.warning(f"Low confidence drop ({avg_no_speech_prob:.2f}): '{text}'")
                return "LOW_CONFIDENCE"
        
        # Word count filter
        if not text or len(text.split()) < 2:
            # Single word command exceptions
            if text_lower not in ["shutdown", "standby", "time", "screenshot"]:
                return None
        
        # Hallucination Blacklist
        hallucinations = [
            "thank you.", "though", "you", "thanks.", "bye.", "okay.", 
            "second bill.", "viscous", "minuteines", "i'm mat", "i don't know.",
            "thanks for watching!", "thanks for watching.", "subscribe."
        ]
        
        if text_lower in hallucinations or "subscribe" in text_lower or "thank you for watching" in text_lower:
            return None

        return text

    def listen(self):
        try:
            import threading
            import requests
            def _send_state(state):
                try: requests.post("http://127.0.0.1:8000/internal/broadcast", json={"type": "voice_state", "payload": {"status": state, "isListening": state == "listening"}}, timeout=0.1)
                except: pass

            with sr.Microphone(sample_rate=16000) as source:
                try:
                    # Broadcast listening
                    threading.Thread(target=_send_state, args=("listening",), daemon=True).start()
                    # Capture audio
                    audio = self.recognizer.listen(source, timeout=12, phrase_time_limit=30)
                    
                    # Broadcast processing
                    threading.Thread(target=_send_state, args=("processing",), daemon=True).start()
                    return self._process_audio(audio)
                except sr.WaitTimeoutError:
                    return "TIMEOUT"
                except Exception as e:
                    logger.error(f"STT Error: {e}")
                    return None
        except Exception as e:
            logger.error(f"Mic Error: {e}")
            return None
