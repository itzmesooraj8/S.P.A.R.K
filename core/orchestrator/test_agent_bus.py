import sys
from unittest.mock import MagicMock

# Mock BEFORE any imports that might trigger the module load
sys.modules["requests"] = MagicMock()
sys.modules["httpx"] = MagicMock()

import pytest
import logging

def test_agent_bus_handler_logging(caplog):
    from core.orchestrator.agent_bus import AgentBus
    bus = AgentBus()

    # Test handler failure
    def failing_handler(event):
        raise ValueError("Handler failed")

    bus.subscribe("test_topic", failing_handler)

    with caplog.at_level(logging.ERROR):
        bus.emit("test_topic", {"data": "test"})

    assert "Error in agent bus handler for topic test_topic" in caplog.text
    assert "Handler failed" in caplog.text

def test_agent_bus_broadcast_logging(caplog):
    import requests
    requests.post.side_effect = Exception("Broadcast failed")

    from core.orchestrator.agent_bus import AgentBus
    bus = AgentBus()

    with caplog.at_level(logging.DEBUG):
        bus.emit("broadcast_topic")

    assert any("Failed to broadcast runtime event to HUD" in record.message for record in caplog.records)
