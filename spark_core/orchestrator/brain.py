import asyncio
from llm.hybrid_engine import HybridLLM
from llm.personality import PersonalityEngine
from memory.session_memory import SessionMemory
from tools.router import ToolRouter

class AIOrchestrator:
    def __init__(self):
        print("🧠 [SPARK] Initializing Brain...")
        self.personality = PersonalityEngine(mode="TACTICAL")
        self.llm = HybridLLM(model="llama3:8b") # or "mistral"
        self.memory = SessionMemory(max_turns=5)
        self.tool_router = ToolRouter()
        
        self.current_task = None
        self.state = {
            "status": "IDLE",
            "personality": "TACTICAL",
            "active_tasks": []
        }

    def get_state(self):
        return self.state
    
    def set_personality(self, mode: str):
        self.personality.set_mode(mode)
        self.state["personality"] = mode

    def cancel_current_task(self):
        """Immediately interrupts any active LLM generation."""
        if self.current_task and not self.current_task.done():
            self.current_task.cancel()
            print("🛑 [SPARK] Force-cancelled active generation task.")

    async def process_stream(self, message: str):
        """Asynchronous generator yielding tokens progressively for the HUD."""
        self.state["status"] = "THINKING"
        print(f"🧠 [SPARK] Stream Processing: {message}")
        
        # 0. Check for explicit manual tool execution command (Backdoor)
        tool_call = self.tool_router.detect_tool_call(message)
        if tool_call:
            try:
                # Do NOT save explicit JSON commands to conversational memory
                async for token in self.tool_router.execute(tool_call):
                    yield token
            except asyncio.CancelledError:
                print(f"⚠️ [SPARK] Tool Execution Cancelled.")
            finally:
                self.state["status"] = "IDLE"
            return
            
        # 1. Add arriving prompt to memory
        self.memory.add_user_message(message)
        
        # 2. Inject previous AI context seamlessly AND load Auto Tool Instructions
        memory_context = self.memory.get_context()
        system_prompt = self.personality.get_prompt(memory_context, include_tools=True)
        
        full_response = ""
        buffer_mode = False
        first_token_seen = False
        
        try:
            # 3. Stream & accumulate
            async for token in self.llm.generate(system_prompt, message):
                full_response += token
                
                if not first_token_seen:
                    if full_response.strip():
                        first_token_seen = True
                        if full_response.lstrip().startswith("{"):
                            buffer_mode = True
                        else:
                            # Flush whatever natural string we accumulated and resume normal streaming
                            for char in full_response:
                                yield char
                elif not buffer_mode:
                    # Normal Stream
                    yield token
                    
            # 4. Stream completed. Evaluate Buffers.
            if buffer_mode:
                tool_call = self.tool_router.detect_tool_call(full_response)
                
                if tool_call:
                    print(f"🔧 [SPARK] Autonomous Tool Call Detected: {tool_call['tool']}")
                    # Reflection Layer Execution
                    tool_result = await self.tool_router.execute_raw(tool_call)
                    
                    reflection_prompt = (
                        f"System Tool Result ({tool_call['tool']}):\n{tool_result}\n\n"
                        f"Respond to the user utilizing this precise system data. Do NOT mention the system tool directly, just use the information naturally."
                    )
                    
                    # Reload Prompt WITHOUT tool instructions to prevent infinite JSON recursion
                    system_prompt_ref = self.personality.get_prompt(memory_context, include_tools=False)
                    
                    reflection_response = ""
                    async for ref_token in self.llm.generate(system_prompt_ref, reflection_prompt):
                        reflection_response += ref_token
                        yield ref_token
                        
                    if reflection_response:
                        self.memory.add_ai_message(reflection_response.strip())
                else:
                    # It started with '{' but wasn't a valid tool call JSON. Flush buffer intact.
                    for char in full_response:
                        yield char
                    if full_response:
                        self.memory.add_ai_message(full_response.strip())
            else:
                # Normal finalization
                if full_response:
                     self.memory.add_ai_message(full_response.strip())
                
        except asyncio.CancelledError:
            print(f"⚠️ [SPARK] Stream Cancelled mid-generation. Discarding partial memory.")
            pass
        finally:
            self.state["status"] = "IDLE"

    async def process_message(self, message: str) -> str:
        """Fallback: Core AI Loop for returning a single full blocking response."""
        self.state["status"] = "THINKING"
        print(f"🧠 [SPARK] Blocking Processing: {message}")
        
        self.memory.add_user_message(message)
        
        memory_context = self.memory.get_context()
        system_prompt = self.personality.get_prompt(memory_context)

        full_response = ""
        async for token in self.llm.generate(system_prompt, message):
            full_response += token

        if full_response:
            self.memory.add_ai_message(full_response.strip())

        # 4. Filter Intent / Execute Tools (Placeholder for Tool Execution Engine)
        # if is_command(response): execute_tool()

        self.state["status"] = "IDLE"
        return full_response

# Example intent check, you can expand this later
def is_command(text: str) -> bool:
    return '[ACTION]' in text
