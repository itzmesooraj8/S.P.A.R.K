import asyncio
import uuid
import traceback
from typing import Callable, Dict, Any, List, Optional

# ---------------------------------------------------------------------------
# Lightweight payload schema validation for core event types.
# Returns (is_valid, error_message_or_None).
# ---------------------------------------------------------------------------
_SCHEMA: Dict[str, List[str]] = {
    "user_input":      ["data", "session_id"],
    "response_token":  ["token"],
    "response_done":   [],
    "tool_execute":    ["tool"],
    "tool_result":     ["tool"],
    "brain_decision":  ["action"],
    "cancel_task":     [],
    "confirm_tool":    ["id", "tool"],
}

def _validate_payload(event_type: str, payload: Any) -> Optional[str]:
    """Returns an error string if payload is invalid, else None."""
    required = _SCHEMA.get(event_type)
    if required is None:
        return None  # Unknown event type — let it through
    if not isinstance(payload, dict):
        return f"payload must be a dict, got {type(payload).__name__}"
    missing = [k for k in required if k not in payload]
    if missing:
        return f"missing required keys: {missing}"
    return None


class EventBus:
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {}
        # Maps handler qualname → set of event types it's already registered for.
        # Used to prevent duplicate registrations on hot-reload.
        self._registered_handler_ids: Dict[str, set] = {}
        self.task_registry: Dict[str, asyncio.Task] = {}

    def subscribe(self, event_type: str):
        def decorator(handler: Callable):
            # Dedup guard: use the handler's qualified name as a stable identity key.
            handler_key = getattr(handler, "__qualname__", None) or repr(handler)
            registered_for = self._registered_handler_ids.setdefault(handler_key, set())
            if event_type in registered_for:
                # Already registered — skip to prevent duplicate fan-out on reload.
                return handler
            registered_for.add(event_type)

            if event_type not in self.subscribers:
                self.subscribers[event_type] = []
            self.subscribers[event_type].append(handler)
            return handler
        return decorator

    def publish(self, event_type: str, payload: Any = None):
        # Event Trace Logging Mode
        print(f"[EVENT] {event_type}")

        # Schema validation — warn but never swallow the event
        err = _validate_payload(event_type, payload)
        if err:
            print(f"⚠️ [EventBus] Schema warning for '{event_type}': {err}")

        if event_type in self.subscribers:
            for handler in self.subscribers[event_type]:
                task_id = str(uuid.uuid4())

                # Phase 2: Structured task tracking
                task = asyncio.create_task(self._safe_execute(handler, payload, task_id))
                self.task_registry[task_id] = task
                task.add_done_callback(lambda t, tid=task_id: self._cleanup_task(t, tid))

    async def _safe_execute(self, handler, payload, task_id):
        try:
            await handler(payload)
        except Exception as e:
            print(f"[EventBus] Task {task_id} failed: {e}")
            raise

    def _cleanup_task(self, task: asyncio.Task, task_id: str):
        if task_id in self.task_registry:
            del self.task_registry[task_id]

        if task.cancelled():
            print(f"[EventBus] Task {task_id} was cancelled.")
        elif task.exception():
            exc = task.exception()
            print(f"[EventBus] Silent failure intercepted in {task_id}: {type(exc).__name__}: {exc}")
            # Do not log full stack trace to stream, but print internally
            traceback.print_exception(type(exc), exc, exc.__traceback__)

event_bus = EventBus()
