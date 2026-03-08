"""
SPARK Command System
────────────────────────────────────────────────────────────────────────────────
Intent routing, command dispatch, and Command Bar orchestration.
"""

from command.intent_router import intent_router, IntentRouter, RoutingRequest, RoutingResponse, ContextInput
from command.dispatcher import execute_routing_decision, DispatchResult

__all__ = [
    'intent_router',
    'IntentRouter',
    'RoutingRequest',
    'RoutingResponse',
    'ContextInput',
    'execute_routing_decision',
    'DispatchResult',
]
