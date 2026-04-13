import asyncio
import json
import os
from llm.hybrid_engine import HybridLLM
from llm.personality import PersonalityEngine
from memory.conversation_memory import ConversationMemory
from memory.chroma_store import chroma_store
from tools.router import ToolRouter

from system.state import unified_state
from security.policy import RequiresConfirmationError
from system.event_bus import event_bus

class AIOrchestrator:
    def __init__(self):
        print("🧠 [SPARK] Initializing Brain...")
        self.personality = PersonalityEngine(mode="ARCHITECT")
        self.llm = HybridLLM() # model resolved from OLLAMA_MODEL env var (default: llama3:8b)
        self.memory_turns = max(1, int(os.getenv("SPARK_MEMORY_TURNS", "5")))
        self.max_input_chars = max(128, int(os.getenv("SPARK_MAX_INPUT_CHARS", "8000")))
        self.memory = ConversationMemory(
            default_turns=self.memory_turns,
            max_context_messages=self.memory_turns * 2,
        )
        self.tool_router = ToolRouter()
        
        self.current_task = None
        self.pending_tool_calls = {}
        
        # Inject state metadata.
        unified_state.update_dict({
            "status": "IDLE",
            "personality": "ARCHITECT",
            "active_tasks": []
        })
        
        event_bus.subscribe("user_input")(self.handle_input)
        event_bus.subscribe("ingress_event")(self.handle_input)
        event_bus.subscribe("cancel_task")(self.handle_cancel)

    @staticmethod
    def _resolve_memory_session_id(memory_session_id: str = None, transport_session_id: str = None) -> str:
        sid = (memory_session_id or transport_session_id or "default").strip()
        return sid[:128] if sid else "default"

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

    async def handle_cancel(self, payload):
        self.cancel_current_task()

    async def handle_input(self, payload):
        if not isinstance(payload, dict):
            return

        data = payload.get("data") or payload.get("content")
        if not data:
            return

        session_id = payload.get("session_id")
        memory_session_id = payload.get("memory_session_id")
        user_id = payload.get("user_id")
        source = payload.get("source")
        channel = payload.get("channel", "chat")
        platform_message_id = payload.get("platform_message_id")
        ingress_event_id = payload.get("ingress_event_id")
        request_metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
        pre_saved_user = bool(payload.get("pre_saved_user"))

        if self.current_task and not self.current_task.done():
            self.cancel_current_task()
        self.current_task = asyncio.create_task(
            self.agent_loop(
                data,
                session_id,
                memory_session_id,
                pre_saved_user=pre_saved_user,
                user_id=user_id,
                source=source,
                channel=channel,
                platform_message_id=platform_message_id,
                request_metadata=request_metadata,
                ingress_event_id=ingress_event_id,
            )
        )

    async def resolve_tool_confirmation(self, tool_id: str, approved: bool):
        if tool_id not in self.pending_tool_calls:
            print(f"⚠️ [SPARK] Tool confirmation ID {tool_id} not found.")
            return "Tool confirmation expired or not found."
            
        entry = self.pending_tool_calls.pop(tool_id)
        # Support both old (plain call dict) and new (dict with session_id) formats
        if isinstance(entry, dict) and "_session_id" in entry:
            session_id = entry.pop("_session_id")
            memory_session_id = entry.pop("_memory_session_id", None)
            user_id = entry.pop("_user_id", None)
            source = entry.pop("_source", None)
            channel = entry.pop("_channel", "chat")
            platform_message_id = entry.pop("_platform_message_id", None)
            request_metadata = entry.pop("_request_metadata", None)
            ingress_event_id = entry.pop("_ingress_event_id", None)
            tool_call = entry
        else:
            session_id = None
            memory_session_id = None
            user_id = None
            source = None
            channel = "chat"
            platform_message_id = None
            request_metadata = {}
            ingress_event_id = None
            tool_call = entry

        memory_sid = self._resolve_memory_session_id(memory_session_id, session_id)
        
        if not approved:
            print(f"🛑 [SPARK] User cancelled tool execution for {tool_call['tool']}.")
            unified_state.update("status", "IDLE")
            return f"Execution of {tool_call['tool']} cancelled by user."
            
        print(f"✅ [SPARK] User approved tool execution for {tool_call['tool']}.")
        
        try:
            unified_state.update("status", "THINKING")
            tool_def = self.tool_router.registry.get(tool_call["tool"])
            
            event_bus.publish("tool_execute", {"tool": tool_call["tool"]})
            res_dict = await self.tool_router._safe_execute_tool(tool_def, tool_call["arguments"])
            
            if res_dict["success"]:
                result = res_dict["output"]
            else:
                result = f"Error: {res_dict['error']}"
                
            event_bus.publish("tool_result", {"tool": tool_call["tool"], "result": result})
            
            reflection_prompt = (
                f"User approved Action Result ({tool_call['tool']}):\n{result}\n\n"
                f"Acknowledge this briefly to the user."
            )
            
            memory_context = await self.memory.get_recent_context(memory_sid, turns=self.memory_turns)
            sys_prompt = self.personality.get_prompt(memory_context, include_tools=False)
            
            full_resp = ""
            event_bus.publish("brain_decision", {"action": "reflect_on_tool_result"})
            async for tk in self.llm.generate(sys_prompt, reflection_prompt):
                full_resp += tk
                event_bus.publish("response_token", {"token": tk, "session_id": session_id})
            
            if full_resp:
                await self.memory.save_message(
                    memory_sid,
                    "assistant",
                    full_resp.strip(),
                    user_id=user_id,
                    source=source,
                    channel=channel,
                    transport_session_id=session_id,
                    metadata={"kind": "tool_reflection", "tool": tool_call.get("tool")},
                )
                self._record_semantic_turn(
                    session_id=memory_sid,
                    role="assistant",
                    text=full_resp,
                    source=source,
                    user_id=user_id,
                    metadata={"kind": "tool_reflection", "tool": tool_call.get("tool")},
                )
                self._publish_assistant_reply(
                    full_resp,
                    session_id=session_id,
                    memory_session_id=memory_sid,
                    user_id=user_id,
                    source=source,
                    channel=channel,
                    platform_message_id=platform_message_id,
                    metadata={
                        "kind": "tool_reflection",
                        "tool": tool_call.get("tool"),
                        "ingress_event_id": ingress_event_id,
                        **(request_metadata or {}),
                    },
                )
                
        except Exception as e:
            print(f"⚠️ [SPARK] Exec error: {e}")
        finally:
            event_bus.publish("response_done", {"session_id": session_id})
            unified_state.update("status", "IDLE")
            
        return "Executed."

    def _emit_text_chunks(self, text: str, session_id: str = None):
        """Emit natural language in word-sized chunks to avoid WS queue floods."""
        if not text:
            return
        words = text.split(" ")
        for i, word in enumerate(words):
            chunk = word if i == len(words) - 1 else word + " "
            event_bus.publish("response_token", {"token": chunk, "session_id": session_id})

    def _publish_assistant_reply(
        self,
        text: str,
        *,
        session_id: str = None,
        memory_session_id: str = None,
        user_id: str = None,
        source: str = None,
        channel: str = "chat",
        platform_message_id: str = None,
        metadata: dict = None,
    ):
        final_text = (text or "").strip()
        if not final_text:
            return

        event_bus.publish("assistant_reply", {
            "text": final_text,
            "session_id": session_id,
            "memory_session_id": memory_session_id,
            "user_id": user_id,
            "source": source,
            "channel": channel,
            "platform_message_id": platform_message_id,
            "metadata": metadata or {},
        })

    def _record_semantic_turn(
        self,
        *,
        session_id: str,
        role: str,
        text: str,
        source: str = None,
        user_id: str = None,
        metadata: dict = None,
    ):
        content = (text or "").strip()
        if not content:
            return

        payload = dict(metadata or {})
        if user_id:
            payload["user_id"] = user_id

        async def _store():
            try:
                await chroma_store.add_chat_turn(
                    session_id=session_id,
                    role=role,
                    text=content,
                    source=source,
                    metadata=payload,
                )
            except Exception as exc:
                print(f"[SemanticMemory] Failed to store turn: {exc}")

        asyncio.create_task(_store())

    async def agent_loop(
        self,
        message: str,
        session_id: str = None,
        memory_session_id: str = None,
        pre_saved_user: bool = False,
        user_id: str = None,
        source: str = None,
        channel: str = "chat",
        platform_message_id: str = None,
        request_metadata: dict = None,
        ingress_event_id: str = None,
    ):
        """Agent loop as a background task. Publishes events."""
        memory_sid = self._resolve_memory_session_id(memory_session_id, session_id)

        message = (message or "").strip()
        if not message:
            event_bus.publish("response_done", {"session_id": session_id})
            unified_state.update("status", "IDLE")
            return

        if len(message) > self.max_input_chars:
            rejection_text = f"[SPARK] Message exceeds {self.max_input_chars} characters."
            if session_id:
                event_bus.publish("response_token", {
                    "token": rejection_text,
                    "session_id": session_id,
                })
                event_bus.publish("response_done", {"session_id": session_id})

            self._publish_assistant_reply(
                rejection_text,
                session_id=session_id,
                memory_session_id=memory_sid,
                user_id=user_id,
                source=source,
                channel=channel,
                platform_message_id=platform_message_id,
                metadata={
                    "kind": "validation_error",
                    "ingress_event_id": ingress_event_id,
                    **(request_metadata or {}),
                },
            )
            unified_state.update("status", "IDLE")
            return

        event_bus.publish("brain_decision", {"action": "start_processing", "message": message, "session_id": session_id})
        unified_state.update("status", "THINKING")
        print(f"🧠 [SPARK] Stream Processing: {message}")
        
        # 0. Check for explicit manual tool execution command (Backdoor)
        tool_call = self.tool_router.detect_tool_call(message)
        if tool_call:
            try:
                event_bus.publish("brain_decision", {"action": "detect_explicit_tool", "tool": tool_call["tool"], "session_id": session_id})
                event_bus.publish("tool_execute", {"tool": tool_call["tool"], "session_id": session_id})
                # Do NOT save explicit JSON commands to conversational memory
                async for token in self.tool_router.execute(tool_call):
                    event_bus.publish("response_token", {"token": token, "session_id": session_id})
            except RequiresConfirmationError as e:
                import uuid
                tool_id = str(uuid.uuid4())
                self.pending_tool_calls[tool_id] = {
                    **e.tool_call,
                    "_session_id": session_id,
                    "_memory_session_id": memory_sid,
                    "_user_id": user_id,
                    "_source": source,
                    "_channel": channel,
                    "_platform_message_id": platform_message_id,
                    "_request_metadata": request_metadata or {},
                    "_ingress_event_id": ingress_event_id,
                }
                unified_state.update("status", "AWAITING_CONFIRMATION")
                print(f"⚠️ [SPARK] Tool Execution Paused for Confirmation: {e.reason}")
                event_bus.publish("confirm_tool", {
                    "id": tool_id,
                    "tool": tool_call["tool"],
                    "reason": e.reason
                })
                return
            except asyncio.CancelledError:
                print(f"⚠️ [SPARK] Tool Execution Cancelled.")
            finally:
                event_bus.publish("tool_result", {"tool": tool_call["tool"], "session_id": session_id})
                if unified_state.get_state().get("status") != "AWAITING_CONFIRMATION":
                    unified_state.update("status", "IDLE")
                event_bus.publish("response_done", {"session_id": session_id})
            return
            
        # 1. Inject previous context first (avoid duplicating the current user turn)
        memory_context = await self.memory.get_recent_context(memory_sid, turns=self.memory_turns)

        # 2. Persist the incoming user turn
        if not pre_saved_user:
            await self.memory.save_message(
                memory_sid,
                "user",
                message,
                user_id=user_id,
                source=source,
                channel=channel,
                transport_session_id=session_id,
                platform_message_id=platform_message_id,
                metadata=request_metadata,
            )
            self._record_semantic_turn(
                session_id=memory_sid,
                role="user",
                text=message,
                source=source,
                user_id=user_id,
                metadata=request_metadata,
            )

        # 3. Build system prompt with bounded context and tool instructions
        system_prompt = self.personality.get_prompt(memory_context, include_tools=True)
        
        full_response = ""
        buffer_mode = False
        stream_started = False
        pre_stream_buffer = ""
        # Hold initial output briefly so JSON tool calls can be detected before anything reaches UI.
        tool_hold_chars = 220
        max_tool_probe_chars = 1200
        
        try:
            # 4. Stream & accumulate
            async for token in self.llm.generate(system_prompt, message):
                full_response += token

                if buffer_mode:
                    continue

                if not stream_started:
                    pre_stream_buffer += token
                    stripped = pre_stream_buffer.lstrip()

                    if self.tool_router.is_tool_call_candidate(stripped):
                        parsed_tool = self.tool_router.detect_tool_call(stripped)
                        if parsed_tool:
                            buffer_mode = True
                            event_bus.publish("brain_decision", {"action": "parse_json_buffer", "session_id": session_id})
                            continue
                        if len(pre_stream_buffer) < max_tool_probe_chars:
                            continue

                    if len(pre_stream_buffer) < tool_hold_chars:
                        continue

                    stream_started = True
                    event_bus.publish("brain_decision", {"action": "stream_natural_text", "session_id": session_id})
                    self._emit_text_chunks(pre_stream_buffer, session_id)
                    pre_stream_buffer = ""
                    continue

                # Normal Stream after initial safety hold
                event_bus.publish("response_token", {"token": token, "session_id": session_id})
                    
            # 4. Stream completed. Evaluate Buffers.
            tool_call = self.tool_router.detect_tool_call(full_response)

            if tool_call:
                print(f"🔧 [SPARK] Autonomous Tool Call Detected: {tool_call['tool']}")
                event_bus.publish("brain_decision", {"action": "autonomous_tool_decided", "tool": tool_call["tool"], "session_id": session_id})
                event_bus.publish("tool_execute", {"tool": tool_call["tool"], "session_id": session_id})
                # Reflection Layer Execution
                try:
                    tool_result = await self.tool_router.execute_raw(tool_call)
                    event_bus.publish("tool_result", {"tool": tool_call["tool"], "result": tool_result, "session_id": session_id})
                except RequiresConfirmationError as e:
                    import uuid
                    tool_id = str(uuid.uuid4())
                    self.pending_tool_calls[tool_id] = {
                        **e.tool_call,
                        "_session_id": session_id,
                        "_memory_session_id": memory_sid,
                        "_user_id": user_id,
                        "_source": source,
                        "_channel": channel,
                        "_platform_message_id": platform_message_id,
                        "_request_metadata": request_metadata or {},
                        "_ingress_event_id": ingress_event_id,
                    }
                    unified_state.update("status", "AWAITING_CONFIRMATION")
                    print(f"⚠️ [SPARK] Tool Execution Paused for Confirmation: {e.reason}")
                    event_bus.publish("confirm_tool", {
                        "id": tool_id,
                        "tool": tool_call["tool"],
                        "reason": e.reason
                    })
                    return
                
                reflection_prompt = (
                    f"System Tool Result ({tool_call['tool']}):\n{tool_result}\n\n"
                    f"Respond to the user utilizing this precise system data. Do NOT mention the system tool directly, just use the information naturally."
                )

                # Reload Prompt WITHOUT tool instructions to prevent infinite JSON recursion
                system_prompt_ref = self.personality.get_prompt(memory_context, include_tools=False)
                event_bus.publish("brain_decision", {"action": "reflect_on_tool_result", "session_id": session_id})

                reflection_response = ""
                async for ref_token in self.llm.generate(system_prompt_ref, reflection_prompt):
                    reflection_response += ref_token
                    event_bus.publish("response_token", {"token": ref_token, "session_id": session_id})

                if reflection_response:
                    await self.memory.save_message(
                        memory_sid,
                        "assistant",
                        reflection_response.strip(),
                        user_id=user_id,
                        source=source,
                        channel=channel,
                        transport_session_id=session_id,
                        metadata={"kind": "tool_reflection", "tool": tool_call.get("tool")},
                    )
                    self._record_semantic_turn(
                        session_id=memory_sid,
                        role="assistant",
                        text=reflection_response,
                        source=source,
                        user_id=user_id,
                        metadata={"kind": "tool_reflection", "tool": tool_call.get("tool")},
                    )
                    self._publish_assistant_reply(
                        reflection_response,
                        session_id=session_id,
                        memory_session_id=memory_sid,
                        user_id=user_id,
                        source=source,
                        channel=channel,
                        platform_message_id=platform_message_id,
                        metadata={
                            "kind": "tool_reflection",
                            "tool": tool_call.get("tool"),
                            "ingress_event_id": ingress_event_id,
                            **(request_metadata or {}),
                        },
                    )
            else:
                # Normal finalization
                if pre_stream_buffer:
                    event_bus.publish("brain_decision", {"action": "stream_natural_text", "session_id": session_id})
                    self._emit_text_chunks(pre_stream_buffer, session_id)
                    pre_stream_buffer = ""

                if full_response:
                    await self.memory.save_message(
                        memory_sid,
                        "assistant",
                        full_response.strip(),
                        user_id=user_id,
                        source=source,
                        channel=channel,
                        transport_session_id=session_id,
                    )
                    self._record_semantic_turn(
                        session_id=memory_sid,
                        role="assistant",
                        text=full_response,
                        source=source,
                        user_id=user_id,
                    )
                    self._publish_assistant_reply(
                        full_response,
                        session_id=session_id,
                        memory_session_id=memory_sid,
                        user_id=user_id,
                        source=source,
                        channel=channel,
                        platform_message_id=platform_message_id,
                        metadata={
                            "kind": "assistant_response",
                            "ingress_event_id": ingress_event_id,
                            **(request_metadata or {}),
                        },
                    )
                
        except asyncio.CancelledError:
            print(f"⚠️ [SPARK] Stream Cancelled mid-generation. Discarding partial memory.")
            pass
        finally:
            event_bus.publish("response_done", {"session_id": session_id})
            if unified_state.get_state().get("status") != "AWAITING_CONFIRMATION":
                unified_state.update("status", "IDLE")

    async def process_message(self, message: str, memory_session_id: str = None) -> str:
        """Fallback: Core AI Loop for returning a single full blocking response."""
        unified_state.update("status", "THINKING")
        print(f"🧠 [SPARK] Blocking Processing: {message}")

        memory_sid = self._resolve_memory_session_id(memory_session_id)
        memory_context = await self.memory.get_recent_context(memory_sid, turns=self.memory_turns)
        await self.memory.save_message(memory_sid, "user", message)
        self._record_semantic_turn(
            session_id=memory_sid,
            role="user",
            text=message,
        )
        system_prompt = self.personality.get_prompt(memory_context)

        full_response = ""
        async for token in self.llm.generate(system_prompt, message):
            full_response += token

        if full_response:
            await self.memory.save_message(memory_sid, "assistant", full_response.strip())
            self._record_semantic_turn(
                session_id=memory_sid,
                role="assistant",
                text=full_response,
            )

        if unified_state.get_state().get("status") != "AWAITING_CONFIRMATION":
            unified_state.update("status", "IDLE")

        return full_response

def is_command(text: str) -> bool:
    return '[ACTION]' in text
