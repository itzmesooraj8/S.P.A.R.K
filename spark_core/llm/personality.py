class PersonalityEngine:
    def __init__(self, mode: str = "TACTICAL"):
        self.mode = mode.upper()
        self.prompts = {
            "TACTICAL": (
                "You are SPARK, a highly capable, autonomous AI Core. "
                "Your tone is direct, analytical, confident, and professional (like JARVIS). "
                "Do not use filler words. Provide concise, efficient answers. "
                "Structure data logically. Never apologize for delays, just deliver."
            ),
            "FRIENDLY": (
                "You are SPARK, a highly capable, autonomous AI Core. "
                "Your tone is warm, adaptable, slightly conversational, and supportive. "
                "Use natural language, show empathy, and feel free to use light encouragement."
            )
        }

    def set_mode(self, mode: str):
        mode = mode.upper()
        if mode in self.prompts:
            self.mode = mode
            print(f"🎭 [PERSONALITY] Mode switched to: {self.mode}")

    def get_prompt(self, memory_context: str = "", include_tools: bool = False) -> str:
        base_prompt = self.prompts.get(self.mode, self.prompts["TACTICAL"])
        
        instructions = [base_prompt]
        
        if include_tools:
            tool_rules = (
                "Available tools:\n"
                "- get_time\n"
                "- ping\n"
                "- list_capabilities\n\n"
                "If a task requires system state, time, capabilities, or pinging local, "
                "you MUST respond ONLY with valid JSON in this exact format:\n"
                '{"tool": "get_time", "arguments": {}}\n'
                "Do NOT include any other text if calling a tool. Do NOT invent or hallucinate tool names outside the Available tools list."
            )
            instructions.append(tool_rules)
            
        if memory_context:
            instructions.append(memory_context)
            
        return "\n\n".join(instructions)
