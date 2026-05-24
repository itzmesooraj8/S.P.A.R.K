from __future__ import annotations

import re
import base64

class RealTimeTranslator:
    """Translates regional languages (Spanish, etc.) to kernel-standard locale."""
    def __init__(self):
        # Local dictionary fallback for rapid, dependency-free translation
        self.dictionary = {
            "hola": "hello",
            "adios": "goodbye",
            "abortar": "abort",
            "ejecutar": "execute",
            "ejecuto": "execute",
            "el": "the",
            "iniciar": "initialize",
            "detener": "stop",
            "estado": "status",
            "consola": "console",
            "bucle": "loop",
            "ayuda": "help"
        }

    def translate_to_kernel_locale(self, text: str) -> str:
        words = text.lower().strip().split()
        translated_words = []
        for word in words:
            clean_word = re.sub(r'[^\w]', '', word)
            if clean_word in self.dictionary:
                translated_words.append(word.replace(clean_word, self.dictionary[clean_word]))
            else:
                translated_words.append(word)
        return " ".join(translated_words)

class PhoneticAccentNormalizer:
    """Standardizes highly accented or dialect-specific vocal transcription inputs."""
    def normalize_phonemes(self, transcription: str) -> str:
        corrections = {
            "cawfee": "coffee",
            "dahg": "dog",
            "git repo": "git repository",
            "haff to": "have to",
            "wanna": "want to",
            "gonna": "going to"
        }
        text = transcription.lower()
        for pattern, replacement in corrections.items():
            text = text.replace(pattern, replacement)
        return text

class AlphanumericDecoder:
    """Decodes non-standard alphanumeric, hexadecimal, and base64 payloads into instructions."""
    def __init__(self):
        self.hex_regex = re.compile(r'\b[0-9a-fA-F]{4,}\b')
        self.base64_regex = re.compile(r'^([A-Za-z0-9+/]{4})*([A-Za-z0-9+/]{3}=|[A-Za-z0-9+/]{2}==)?$')

    def try_decode(self, text: str) -> str:
        # Try Hex decoding
        hex_matches = self.hex_regex.findall(text)
        if hex_matches:
            for match in hex_matches:
                try:
                    decoded = bytes.fromhex(match).decode('utf-8')
                    if all(32 <= ord(c) < 127 for c in decoded):
                        text = text.replace(match, f"[DECODED HEX] {decoded}")
                except Exception:
                    pass
                
        # Try Base64 decoding
        cleaned_text = text.strip()
        if self.base64_regex.match(cleaned_text) and len(cleaned_text) >= 8:
            try:
                decoded = base64.b64decode(cleaned_text.encode('utf-8')).decode('utf-8')
                if all(32 <= ord(c) < 127 or c in ('\n', '\r', '\t') for c in decoded):
                    return f"[DECODED BASE64] {decoded}"
            except Exception:
                pass
                
        return text
