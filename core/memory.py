from enum import Enum
from functools import lru_cache
import uuid, chromadb

class MemoryCategory(str, Enum):
    FACT = "fact"          # "My name is Sooraj", "I live in Kozhikode"
    PREFERENCE = "pref"    # "I prefer dark mode", "I like Python"
    TASK = "task"          # "I have an exam Friday", "remind me to call mom"
    CONVERSATION = "conv"  # General chat history

import logging
_logger = logging.getLogger("SPARK_MEMORY")


@lru_cache(maxsize=1)
def _load_encoder():
    try:
        from sentence_transformers import SentenceTransformer as _ST

        _logger.info("Loading SentenceTransformer encoder (lazy)...")
        encoder = _ST("all-MiniLM-L6-v2")
        _logger.info("SentenceTransformer encoder ready.")
        return encoder
    except Exception as _e:
        _logger.error(f"SentenceTransformer failed to load: {_e}")
        return None

class MemoryStore:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=".spark_memory")
        self.collection = self.client.get_or_create_collection("spark_v2")
        self.encoder = None

    def _get_encoder(self):
        if self.encoder is None:
            self.encoder = _load_encoder()
        return self.encoder

    def store(self, text: str,
              category: MemoryCategory = MemoryCategory.CONVERSATION) -> None:
        encoder = self._get_encoder()
        if encoder is None:
            return
        try:
            embedding = encoder.encode([text])[0].tolist()
            self.collection.add(
                documents=[text],
                embeddings=[embedding],
                metadatas=[{"category": category.value}],
                ids=[str(uuid.uuid4())],
            )
        except Exception as exc:
            _logger.warning("Memory store skipped: %s", exc)

    def recall(self, query: str, top_k: int = 5,
               category: MemoryCategory = None) -> list[str]:
        encoder = self._get_encoder()
        if encoder is None:
            return []
        try:
            if self.collection.count() == 0:
                return []
            embedding = encoder.encode([query])[0].tolist()
            kwargs = dict(
                query_embeddings=[embedding],
                n_results=min(top_k, self.collection.count()),
            )
            if category:
                kwargs["where"] = {"category": category.value}
            results = self.collection.query(**kwargs)
            return results["documents"][0] if results["documents"] else []
        except Exception as exc:
            _logger.warning("Memory recall skipped: %s", exc)
            return []

    def extract_and_store_facts(self, user_input: str) -> None:
        """Auto-detect and store personal facts from user messages."""
        fact_triggers = [
            "my name is", "i am", "i live in", "i work at",
            "remember that", "don't forget", "i prefer", "i like",
            "i have", "i need to", "my exam", "my birthday",
        ]
        lower = user_input.lower()
        if any(t in lower for t in fact_triggers):
            try:
                self.store(user_input, MemoryCategory.FACT)
            except Exception as exc:
                _logger.warning("Fact extraction skipped: %s", exc)

    def count(self) -> int:
        try:
            return self.collection.count()
        except Exception:
            return 0