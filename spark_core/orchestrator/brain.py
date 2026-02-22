import asyncio
import json
from llm.hybrid_engine import HybridLLM
from llm.personality import PersonalityEngine
from memory.session_memory import SessionMemory
from tools.router import ToolRouter

from system.state import unified_state
from security.policy import RequiresConfirmationError

class AIOrchestrator:
    def __init__(self):
        print("🧠 [SPARK] Initializing Brain...")
        self.personality = PersonalityEngine(mode="TACTICAL")
        self.llm = HybridLLM(model="llama3:8b") # or "mistral"
        self.memory = SessionMemory(max_turns=5)
        self.tool_router = ToolRouter()
        
        self.current_task = None
        self.pending_tool_calls = {}
        
        # Inject state metadata.
        unified_state.update_dict({
            "status": "IDLE",
            "personality": "TACTICAL",
            "active_tasks": []
        })

    def get_state(self):
        return unified_state.get_state()
    
    def set_personality(self, mode: str):
        self.personality.set_mode(mode)
        unified_state.update("personality", mode)

    def cancel_current_task(self):
        """Immediately interrupts any active LLM generation."""
        if self.current_task and not self.current_task.done():
            self.current_task.cancel()
            print("🛑 [SPARK] Force-cancelled active generation task.")

    async def resolve_tool_confirmation(self, tool_id: str, approved: bool):
        if tool_id not in self.pending_tool_calls:
            print(f"⚠️ [SPARK] Tool confirmation ID {tool_id} not found.")
            return "Tool confirmation expired or not found."
            
        tool_call = self.pending_tool_calls.pop(tool_id)
        
        if not approved:
            print(f"🛑 [SPARK] User cancelled tool execution for {tool_call['tool']}.")
            unified_state.update("status", "IDLE")
            return f"Execution of {tool_call['tool']} cancelled by user."
            
        print(f"✅ [SPARK] User approved tool execution for {tool_call['tool']}.")
        
        try:
            unified_state.update("status", "THINKING")
            handler = self.tool_router.registry.get(tool_call["tool"]).handler
            result = await handler(tool_call["arguments"])
            
            reflection_prompt = (
                f"User approved Action Result ({tool_call['tool']}):\n{result}\n\n"
                f"Acknowledge this briefly to the user."
            )
            
            from ws.manager import ws_manager
            memory_context = self.memory.get_context()
            sys_prompt = self.personality.get_prompt(memory_context, include_tools=False)
            
            full_resp = ""
            async for tk in self.llm.generate(sys_prompt, reflection_prompt):
                full_resp += tk
                # Push the explicit answer to WS
                await ws_manager.broadcast(json.dumps({"type": "AI_TOKEN", "token": tk}), "ai")
            
            if full_resp:
                self.memory.add_ai_message(full_resp.strip())
                
        except Exception as e:
            print(f"⚠️ [SPARK] Exec error: {e}")
        finally:
            unified_state.update("status", "IDLE")
            
        return "Executed."

    async def process_stream(self, message: str):
        """Asynchronous generator yielding tokens progressively for the HUD."""
        unified_state.update("status", "THINKING")
        print(f"🧠 [SPARK] Stream Processing: {message}")
        
        # 0. Check for explicit manual tool execution command (Backdoor)
        tool_call = self.tool_router.detect_tool_call(message)
        if tool_call:
            try:
                # Do NOT save explicit JSON commands to conversational memory
                async for token in self.tool_router.execute(tool_call):
                    yield token
            except RequiresConfirmationError as e:
                import uuid
                from ws.manager import ws_manager
                tool_id = str(uuid.uuid4())
                self.pending_tool_calls[tool_id] = e.tool_call
                unified_state.update("status", "AWAITING_CONFIRMATION")
                print(f"⚠️ [SPARK] Tool Execution Paused for Confirmation: {e.reason}")
                await ws_manager.broadcast(json.dumps({
                    "type": "CONFIRM_TOOL",
                    "id": tool_id,
                    "tool": tool_call["tool"],
                    "reason": e.reason
                }), "system")
                return
            except asyncio.CancelledError:
                print(f"⚠️ [SPARK] Tool Execution Cancelled.")
            finally:
                if unified_state.get_state().get("status") != "AWAITING_CONFIRMATION":
                    unified_state.update("status", "IDLE")
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
                    try:
                        tool_result = await self.tool_router.execute_raw(tool_call)
                    except RequiresConfirmationError as e:
                        import uuid
                        from ws.manager import ws_manager
                        tool_id = str(uuid.uuid4())
                        self.pending_tool_calls[tool_id] = e.tool_call
                        unified_state.update("status", "AWAITING_CONFIRMATION")
                        print(f"⚠️ [SPARK] Tool Execution Paused for Confirmation: {e.reason}")
                        await ws_manager.broadcast(json.dumps({
                            "type": "CONFIRM_TOOL",
                            "id": tool_id,
                            "tool": tool_call["tool"],
                            "reason": e.reason
                        }), "system")
                        return
                    
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
            if unified_state.get_state().get("status") != "AWAITING_CONFIRMATION":
                unified_state.update("status", "IDLE")

    async def process_message(self, message: str) -> str:
        """Fallback: Core AI Loop for returning a single full blocking response."""
        unified_state.update("status", "THINKING")
        print(f"🧠 [SPARK] Blocking Processing: {message}")
        
        self.memory.add_user_message(message)
        
        memory_context = self.memory.get_context()
        system_prompt = self.personality.get_prompt(memory_context)

        full_response = ""
        async for token in self.llm.generate(system_prompt, message):
            full_response += token

        if full_response:
            self.memory.add_ai_message(full_response.strip())

        if unified_state.get_state().get("status") != "AWAITING_CONFIRMATION":
            unified_state.update("status", "IDLE")

        return full_response

def is_command(text: str) -> bool:
    return '[ACTION]' in text
