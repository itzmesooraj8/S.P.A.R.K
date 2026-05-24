from __future__ import annotations

class SSMLExpressionFormatter:
    """Transforms response text into SSML markup matching target emotional states."""
    def generate_ssml(self, text: str, emotion: str) -> str:
        # Options: excited, empathetic, deadpan
        if emotion == "excited":
            rate = "+15%"
            pitch = "+5Hz"
            volume = "loud"
        elif emotion == "empathetic":
            rate = "-10%"
            pitch = "-2Hz"
            volume = "medium"
        else: # deadpan
            rate = "+5%"
            pitch = "-10Hz"
            volume = "soft"
            
        ssml = (
            f"<speak><prosody rate='{rate}' pitch='{pitch}' volume='{volume}'>"
            f"{text}"
            f"</prosody></speak>"
        )
        return ssml

class AdaptiveBehaviorHeuristic:
    """Adapts verbosity and technical depth based on operational stress and urgency metrics."""
    def calculate_verbosity(self, stress_score: float, urgency_score: float) -> tuple[int, bool]:
        """
        Returns (max_words, technical_verbosity_flag).
        Reduces verbal density and disables technical complexity under high system or user stress.
        """
        if stress_score > 0.75 or urgency_score > 0.80:
            return 30, False  # Ultra-concise, operational summaries only, no technical jargon
        if stress_score > 0.40 or urgency_score > 0.40:
            return 70, True   # Moderate length, keep technical details
        return 120, True      # Full detailed analysis, high verbosity
