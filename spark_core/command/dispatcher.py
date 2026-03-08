"""
SPARK Command Dispatcher
────────────────────────────────────────────────────────────────────────────────
Executes routing decisions made by the Intent Router.
Handles module activation, parameter forwarding, and response composition.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel

from command.intent_router import RoutingDecision, ModuleTarget


class DispatchResult(BaseModel):
    """Result of command dispatch execution."""
    success: bool
    module: str
    action: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    message: str = ""


async def execute_routing_decision(decision: RoutingDecision) -> DispatchResult:
    """
    Execute a routing decision by invoking the appropriate module handler.
    
    This function acts as a dispatcher — it takes a RoutingDecision and calls
    the corresponding module's API or handler function.
    """
    
    try:
        # Module handlers are called based on target_module and action
        
        if decision.target_module == ModuleTarget.MUSIC:
            return await _execute_music(decision)
        
        elif decision.target_module == ModuleTarget.SECURITY:
            return await _execute_security(decision)
        
        elif decision.target_module == ModuleTarget.NEURAL_SEARCH:
            return await _execute_neural_search(decision)
        
        elif decision.target_module == ModuleTarget.SCHEDULER:
            return await _execute_scheduler(decision)
        
        elif decision.target_module == ModuleTarget.BROWSER:
            return await _execute_browser(decision)
        
        elif decision.target_module == ModuleTarget.GLOBE:
            return await _execute_globe(decision)
        
        elif decision.target_module == ModuleTarget.MODE:
            return await _execute_mode(decision)
        
        elif decision.target_module == ModuleTarget.PLUGIN:
            return await _execute_plugin(decision)
        
        elif decision.target_module == ModuleTarget.LLM:
            return await _execute_llm(decision)
        
        else:
            return DispatchResult(
                success=False,
                module=decision.target_module.value,
                action=decision.action,
                error="Unknown target module",
                message=f"Cannot dispatch to unrecognized module: {decision.target_module}"
            )
    
    except Exception as exc:
        return DispatchResult(
            success=False,
            module=decision.target_module.value,
            action=decision.action,
            error=str(exc),
            message=f"Dispatch error: {exc}"
        )


# ── Module Handlers ────────────────────────────────────────────────────────────

async def _execute_music(decision: RoutingDecision) -> DispatchResult:
    """Route to music module."""
    query = decision.parameters.get('query', '')
    action = decision.action
    
    # The command bar or downstream caller will use this info to:
    # 1. Switch frontend to music module
    # 2. If action='play', trigger search and playback with the query
    # 3. If action='pause', send pause command
    
    return DispatchResult(
        success=True,
        module='music',
        action=action,
        result={
            'module': 'music',
            'action': action,
            'query': query,
            'instruction': f"Music module: {action}" + (f" '{query}'" if query else ""),
        },
        message=f"Music: {action}" + (f" '{query}'" if query else "")
    )


async def _execute_security(decision: RoutingDecision) -> DispatchResult:
    """Route to security module."""
    action = decision.action  # 'scan' or 'check'
    
    return DispatchResult(
        success=True,
        module='security',
        action=action,
        result={
            'module': 'security',
            'action': action,
            'instruction': f"Security module: {action}",
        },
        message=f"Security: initiating {action}"
    )


async def _execute_neural_search(decision: RoutingDecision) -> DispatchResult:
    """Route to neural search module."""
    query = decision.parameters.get('query', decision.enriched_query)
    
    return DispatchResult(
        success=True,
        module='neural_search',
        action='search',
        result={
            'module': 'neural_search',
            'action': 'search',
            'query': query,
            'instruction': f"Search knowledge base for: {query}",
        },
        message=f"Searching: {query}"
    )


async def _execute_scheduler(decision: RoutingDecision) -> DispatchResult:
    """Route to scheduler module."""
    action = decision.action  # 'remind' or 'schedule'
    text = decision.parameters.get('text', 'reminder')
    time_str = decision.parameters.get('time', '')
    
    message = f"{action.capitalize()}: {text}"
    if time_str:
        message += f" at {time_str}"
    
    return DispatchResult(
        success=True,
        module='scheduler',
        action=action,
        result={
            'module': 'scheduler',
            'action': action,
            'text': text,
            'time': time_str,
            'instruction': message,
        },
        message=message
    )


async def _execute_browser(decision: RoutingDecision) -> DispatchResult:
    """Route to browser agent."""
    url = decision.parameters.get('url')
    action = decision.action
    
    if action == 'navigate' and url:
        message = f"Opening: {url}"
    else:
        message = f"Browser: {action}"
    
    return DispatchResult(
        success=True,
        module='browser',
        action=action,
        result={
            'module': 'browser',
            'action': action,
            'url': url or '',
            'instruction': message,
        },
        message=message
    )


async def _execute_globe(decision: RoutingDecision) -> DispatchResult:
    """Route to globe monitor."""
    filter_str = decision.parameters.get('filter', '')
    action = decision.action
    
    message = f"Globe: {action}"
    if filter_str:
        message += f" - {filter_str}"
    
    return DispatchResult(
        success=True,
        module='globe',
        action=action,
        result={
            'module': 'globe',
            'action': action,
            'filter': filter_str,
            'instruction': message,
        },
        message=message
    )


async def _execute_mode(decision: RoutingDecision) -> DispatchResult:
    """Route to mode/routine system (placeholder for now)."""
    
    return DispatchResult(
        success=True,
        module='mode',
        action='activate',
        result={
            'module': 'mode',
            'action': 'activate',
            'instruction': "Mode system coming soon",
        },
        message="Mode engine is under development"
    )


async def _execute_plugin(decision: RoutingDecision) -> DispatchResult:
    """Route to plugin system."""
    
    return DispatchResult(
        success=True,
        module='plugin',
        action=decision.action,
        result={
            'module': 'plugin',
            'action': decision.action,
            'instruction': f"Plugin system: {decision.action}",
        },
        message=f"Plugin: {decision.action}"
    )


async def _execute_llm(decision: RoutingDecision) -> DispatchResult:
    """Route to LLM for direct conversation."""
    query = decision.enriched_query or decision.parameters.get('query', '')
    
    return DispatchResult(
        success=True,
        module='llm',
        action='analyze',
        result={
            'module': 'llm',
            'action': 'analyze',
            'query': query,
            'instruction': f"LLM: {query}",
        },
        message="Sending to AI for analysis..."
    )
