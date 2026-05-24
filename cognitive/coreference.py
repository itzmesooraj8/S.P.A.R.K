from __future__ import annotations

import re

class LocalCorefResolver:
    def resolve_pronouns(self, text: str, history_entities: list[str]) -> str:
        """Resolves pronouns (it, this, that, them) to recently touched mechanical/system entities."""
        if not history_entities:
            return text

        words = text.split()
        resolved_words = []
        for word in words:
            clean = re.sub(r'[^\w]', '', word).lower()
            if clean in ("it", "this", "that", "them"):
                # Substitute pronoun with the last active entity
                resolved_words.append(history_entities[-1])
            else:
                resolved_words.append(word)

        return " ".join(resolved_words)
