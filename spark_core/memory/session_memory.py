from typing import List, Dict

class SessionMemory:
    """
    Manages short-term conversational context (sliding window buffer).
    Keeps a strict token/turn budget to prevent context window overflow.
    """
    def __init__(self, max_turns: int = 5):
        # 1 turn = user message + ai message
        self.max_messages = max_turns * 2
        self.history: List[Dict[str, str]] = []
        print(f"🧠 [MEMORY] Session history buffer initialized. Capacity: {max_turns} turns.")

    def add_user_message(self, text: str):
        self.history.append({"role": "User", "content": text})
        self._trim_if_needed()

    def add_ai_message(self, text: str):
        self.history.append({"role": "SPARK", "content": text})
        self._trim_if_needed()

    def get_context(self) -> str:
        """Returns string-formatted conversational log for prompt injection."""
        if not self.history:
            return ""
        
        context = "[Context for reference only (do not mention unless relevant)]\n"
        for msg in self.history:
            context += f"{msg['role']}: {msg['content']}\n"
        return context

    def _trim_if_needed(self):
        if len(self.history) > self.max_messages:
            self.history = self.history[-self.max_messages:]

    def clear(self):
        self.history = []
