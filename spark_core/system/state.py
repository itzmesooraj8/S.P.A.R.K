import asyncio
import time
from typing import Dict, Any, Callable, List, Awaitable

class UnifiedState:
    def __init__(self):
        self._init_state()

    def _init_state(self):
        self._state: Dict[str, Any] = {
            "status": "IDLE",
            "personality": "TACTICAL",
            "active_tasks": [],
            "user_state": {},
            "device_state": {},
            "security_context": {"capabilities": ["base_user", "system_admin"]},
            "metrics": {"cpu": 0, "ram": 0, "disk": 0, "timestamp": 0},
            "code_graph": {"nodes": [], "edges": []},
            "test_registry": [],
            "test_history": []
        }
        self._subscribers: List[Callable[[Dict[str, Any], int, float], None]] = []
        self._async_subscribers: List[Callable[[Dict[str, Any], int, float], Awaitable[None]]] = []
        self._state_version = 0

    def get_state(self) -> Dict[str, Any]:
        return self._state.copy()

    def update(self, key: str, value: Any):
        self._state[key] = value
        self._state_version += 1
        self._notify_subscribers()

    def update_dict(self, updates: Dict[str, Any]):
        for k, v in updates.items():
            self._state[k] = v
        self._state_version += 1
        self._notify_subscribers()

    def _notify_subscribers(self):
        current_time = time.time()
        for sub in self._subscribers:
            try:
                sub(self._state, self._state_version, current_time)
            except Exception as e:
                print(f"⚠️ [UnifiedState] Sync subscriber error: {e}")
                
        for sub in self._async_subscribers:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(sub(self._state, self._state_version, current_time))
            except RuntimeError:
                # No running event loop yet (e.g. during __init__)
                pass
            except Exception as e:
                print(f"⚠️ [UnifiedState] Async subscriber error: {e}")

    def subscribe(self, callback: Callable[[Dict[str, Any], int, float], None]):
        self._subscribers.append(callback)

    def subscribe_async(self, callback: Callable[[Dict[str, Any], int, float], Awaitable[None]]):
        self._async_subscribers.append(callback)

unified_state = UnifiedState()
