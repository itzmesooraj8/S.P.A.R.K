"""
SPARK Intent Router
────────────────────────────────────────────────────────────────────────────────
Dispatch layer that classifies queries and routes them to the correct handler.
Uses a three-layer classification approach to minimize LLM invocation.

Layer 1: Fast regex pattern matching (~0 ms latency)
Layer 2: Keyword-based classifier for ambiguous cases (immediate)
Layer 3: LLM routing fallback (only if layers 1 & 2 are uncertain)

Context Enrichment:
  - Resolves pronouns ("this", "that", "it") using selectedItem from context
  - Injects active module and alert context into routing decision
  - Returns concrete queries to downstream handlers
"""

import re
import asyncio
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum

from llm.model_router import model_router, TaskType, LatencyClass
from pydantic import BaseModel


class ModuleTarget(str, Enum):
    """Valid target modules for routing."""
    MUSIC = "music"
    SECURITY = "security"
    NEURAL_SEARCH = "neural_search"
    SCHEDULER = "scheduler"
    BROWSER = "browser"
    GLOBE = "globe"
    LLM = "llm"  # Direct LLM conversation
    MODE = "mode"  # Routine/mode management
    PLUGIN = "plugin"  # Plugin management
    UNKNOWN = "unknown"


@dataclass
class ContextItem:
    """Represents a selected item in the UI context."""
    module: str  # 'globe', 'security', 'neural_search', etc.
    item_type: str  # 'earthquake', 'alert', 'search_result', etc.
    data: Dict[str, Any] = field(default_factory=dict)
    label: str = ""  # Human-readable description


@dataclass
class RoutingDecision:
    """Result of intent routing."""
    target_module: ModuleTarget
    action: str  # e.g., "play", "scan", "search", "navigate"
    parameters: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.5  # 0.0 to 1.0
    reasoning: str = ""
    enriched_query: str = ""  # Query after context substitution
    requires_llm: bool = False  # Whether LLM is needed for execution


# ── Pattern Definitions (Layer 1) ──────────────────────────────────────────────

_PATTERNS = {
    ModuleTarget.MUSIC: [
        r'\b(?:play|music|song|album|artist|spotify|sound|audio)\b',
        r'\b(?:pause|stop|resume|next|previous|skip|shuffle)\b',
    ],
    ModuleTarget.SECURITY: [
        r'\b(?:scan|threat|firewall|vulnerability|attack|breach|exploit|malware)\b',
        r'\b(?:port scan|security check|audit|intrusion|defense)\b',
    ],
    ModuleTarget.NEURAL_SEARCH: [
        r'\b(?:search|find|look up|lookup|query|research|investigate)\b',
        r'\b(?:knowledge|document|file|knowledge base)\b',
    ],
    ModuleTarget.SCHEDULER: [
        r'\b(?:remind|reminder|schedule|at \d{1,2}:\d{2}|tomorrow|next week|in \d+\s+(?:minute|hour|day))\b',
        r'\b(?:set alarm|schedule task|calendar|due)\b',
    ],
    ModuleTarget.BROWSER: [
        r'(?:https?://|www\.)[^\s]+',  # URL pattern
        r'\b(?:open|browse|navigate|visit|go to)\b',
    ],
    ModuleTarget.GLOBE: [
        r'\b(?:globe|world|event|country|region|geopolit|conflict|war|missile|sanction)\b',
        r'\b(?:earthquake|tsunami|natural|disaster|alert|intelligence)\b',
        r'(?:^|[\s,])(?:USA|UK|Russia|China|India|Japan|Germany|France|Brazil|Mexico|Canada|Australia|[A-Z][a-z]+stan)(?:[\s,]|$)',
    ],
    ModuleTarget.MODE: [
        r'\b(?:mode|routine|activate|switch|focus|dev mode|monitor mode)\b',
        r'\b(?:/mode)\b',
    ],
}

# Compile regex patterns with case-insensitive matching
_COMPILED_PATTERNS = {}
for module, pattern_list in _PATTERNS.items():
    _COMPILED_PATTERNS[module] = [re.compile(p, re.IGNORECASE) for p in pattern_list]


# ── Keyword Vocabulary (Layer 2) ────────────────────────────────────────────────

_KEYWORD_MAP = {
    ModuleTarget.MUSIC: {
        'keywords': ['play', 'music', 'song', 'album', 'artist', 'pause', 'resume', 'skip', 'shuffle'],
        'weight': 1.0
    },
    ModuleTarget.SECURITY: {
        'keywords': ['scan', 'threat', 'firewall', 'vulnerability', 'attack', 'breach', 'security'],
        'weight': 1.0
    },
    ModuleTarget.NEURAL_SEARCH: {
        'keywords': ['search', 'find', 'lookup', 'research', 'investigate', 'knowledge'],
        'weight': 0.9
    },
    ModuleTarget.SCHEDULER: {
        'keywords': ['remind', 'schedule', 'alarm', 'calendar', 'time', 'when'],
        'weight': 0.9
    },
    ModuleTarget.BROWSER: {
        'keywords': ['browse', 'open', 'navigate', 'visit', 'website', 'url'],
        'weight': 0.8
    },
    ModuleTarget.GLOBE: {
        'keywords': ['globe', 'world', 'country', 'event', 'conflict', 'geopolit', 'earthquake'],
        'weight': 0.85
    },
}


# ── Layer 1: Pattern Matching ──────────────────────────────────────────────────

def _classify_layer1(query: str) -> Optional[ModuleTarget]:
    """
    Fast regex pattern matching. Returns None if no clear match.
    """
    query_lower = query.lower()
    
    for module, patterns in _COMPILED_PATTERNS.items():
        for pattern in patterns:
            if pattern.search(query_lower):
                return module
    
    return None


# ── Layer 2: Keyword Classifier ────────────────────────────────────────────────

def _classify_layer2(query: str) -> Optional[ModuleTarget]:
    """
    Keyword-based voting. Returns module with highest confidence; None if tied.
    """
    query_lower = query.lower()
    scores: Dict[str, float] = {}
    
    for module, vocab in _KEYWORD_MAP.items():
        keywords = vocab['keywords']
        weight = vocab['weight']
        
        # Count keyword matches
        matches = sum(1 for kw in keywords if kw in query_lower)
        score = matches * weight
        
        if score > 0:
            scores[module] = score
    
    if not scores:
        return None
    
    # Return highest-scoring module
    best = max(scores.items(), key=lambda x: x[1])
    return best[0]


# ── Layer 3: LLM Fallback ──────────────────────────────────────────────────────

async def _classify_layer3(query: str, context: Optional[ContextItem] = None) -> RoutingDecision:
    """
    LLM-based routing fallback. Only called if layers 1 & 2 are uncertain.
    """
    
    context_str = ""
    if context:
        context_str = f"\nCurrent context: User is viewing {context.module} module, selected item: {context.label}"
    
    routing_prompt = f"""You are SPARK's intent classifier. Classify this command into ONE of these categories:
- music: play songs, control playback
- security: scan for threats, firewall checks
- neural_search: search knowledge base, find documents
- scheduler: set reminders, schedule tasks
- browser: open website, navigate URL
- globe: view world events, geopolitical intelligence
- llm: general conversation, analysis, brainstorming
- mode: activate routines or modes
- plugin: manage plugins
- unknown: unclear intent

Command: "{query}"{context_str}

Respond with exactly one word: the module name. Nothing else."""
    
    try:
        response = await model_router.route_completion(
            prompt=routing_prompt,
            task_type=TaskType.CLASSIFICATION,
            latency_class=LatencyClass.FAST,
            max_tokens=1,
        )
        
        module_name = response.strip().lower()
        try:
            return ModuleTarget(module_name)
        except ValueError:
            return ModuleTarget.UNKNOWN
    except Exception as exc:
        print(f"⚠️ [IntentRouter] Layer 3 LLM error: {exc}")
        return ModuleTarget.UNKNOWN


# ── Context Enrichment ─────────────────────────────────────────────────────────

_PRONOUN_PATTERNS = {
    'demonstrative': [r'\bthis\b', r'\bthat\b', r'\bthese\b', r'\bthose\b'],
    'personal': [r'\bit\b', r'\bthey\b', r'\bthey\b'],
    'possessive': [r'\bits\b', r'\btheir\b'],
    'relative': [r'\bwhat.*looking at\b', r'\bwhat.*viewing\b', r'\bthe selected\b'],
}

_COMPILED_PRONOUN_PATTERNS = {
    k: [re.compile(p, re.IGNORECASE) for p in patterns]
    for k, patterns in _PRONOUN_PATTERNS.items()
}


def _has_pronoun_reference(query: str) -> bool:
    """Check if query contains ambiguous pronouns that need context resolution."""
    for pattern_list in _COMPILED_PRONOUN_PATTERNS.values():
        for pattern in pattern_list:
            if pattern.search(query):
                return True
    return False


def _enrich_query_with_context(query: str, context: Optional[ContextItem]) -> str:
    """
    Replace pronouns and vague references with concrete context.
    Example: "Tell me more about this" → "Tell me more about the M6.2 earthquake near lat 34.5"
    """
    if not context or not _has_pronoun_reference(query):
        return query
    
    # Build context description
    context_label = context.label or f"{context.item_type} from {context.module}"
    
    # Replace demonstratives ("this", "that")
    enriched = re.sub(
        r'\bthis\b|\bthat\b|\bthese\b|\bthose\b',
        f"the {context_label}",
        query,
        flags=re.IGNORECASE
    )
    
    # Replace personal pronouns ("it")
    enriched = re.sub(
        r'\bit\b',
        f"the {context_label}",
        enriched,
        flags=re.IGNORECASE
    )
    
    return enriched


# ── Main Router ────────────────────────────────────────────────────────────────

class IntentRouter:
    """
    Three-layer intent router: patterns → keywords → LLM.
    """
    
    def __init__(self):
        self.total_routes = 0
        self.layer1_hits = 0
        self.layer2_hits = 0
        self.layer3_hits = 0
    
    async def route(
        self,
        query: str,
        context: Optional[ContextItem] = None,
    ) -> RoutingDecision:
        """
        Classify a query and return routing decision.
        Optionally enriches query with context before classification.
        """
        self.total_routes += 1
        
        # Enrich query with context if needed
        enriched_query = _enrich_query_with_context(query, context)
        
        # Layer 1: Pattern matching
        module = _classify_layer1(enriched_query)
        if module and module != ModuleTarget.UNKNOWN:
            self.layer1_hits += 1
            return RoutingDecision(
                target_module=module,
                action=self._extract_action(enriched_query, module),
                parameters=self._extract_parameters(enriched_query, module),
                confidence=0.95,
                reasoning="Pattern match (Layer 1)",
                enriched_query=enriched_query,
            )
        
        # Layer 2: Keyword classifier
        module = _classify_layer2(enriched_query)
        if module and module != ModuleTarget.UNKNOWN:
            self.layer2_hits += 1
            return RoutingDecision(
                target_module=module,
                action=self._extract_action(enriched_query, module),
                parameters=self._extract_parameters(enriched_query, module),
                confidence=0.75,
                reasoning="Keyword match (Layer 2)",
                enriched_query=enriched_query,
            )
        
        # Layer 3: LLM fallback
        self.layer3_hits += 1
        module = await _classify_layer3(enriched_query, context)
        return RoutingDecision(
            target_module=module,
            action=self._extract_action(enriched_query, module),
            parameters=self._extract_parameters(enriched_query, module),
            confidence=0.6 if module != ModuleTarget.UNKNOWN else 0.3,
            reasoning="LLM classification (Layer 3)",
            enriched_query=enriched_query,
            requires_llm=True,
        )
    
    def _extract_action(self, query: str, module: ModuleTarget) -> str:
        """Extract action verb from query based on module."""
        query_lower = query.lower()
        
        if module == ModuleTarget.MUSIC:
            if any(w in query_lower for w in ['pause', 'stop']):
                return 'pause'
            if any(w in query_lower for w in ['resume', 'continue', 'play']):
                return 'play'
            if any(w in query_lower for w in ['next', 'skip']):
                return 'skip'
            return 'play'
        
        elif module == ModuleTarget.SECURITY:
            return 'scan' if 'scan' in query_lower else 'check'
        
        elif module == ModuleTarget.NEURAL_SEARCH:
            return 'search'
        
        elif module == ModuleTarget.SCHEDULER:
            return 'remind' if 'remind' in query_lower else 'schedule'
        
        elif module == ModuleTarget.BROWSER:
            return 'navigate' if 'open' in query_lower or 'browse' in query_lower else 'screenshot'
        
        elif module == ModuleTarget.GLOBE:
            return 'filter' if any(w in query_lower for w in ['filter', 'show']) else 'view'
        
        elif module == ModuleTarget.MODE:
            return 'activate'
        
        elif module == ModuleTarget.LLM:
            return 'analyze'
        
        return 'execute'
    
    def _extract_parameters(self, query: str, module: ModuleTarget) -> Dict[str, Any]:
        """Extract module-specific parameters from query."""
        params = {}
        
        if module == ModuleTarget.MUSIC:
            # Try to extract song/artist name
            # Simple heuristic: text after "play"
            match = re.search(r'play\s+(.+?)(?:\s+by|\s*$)', query, re.IGNORECASE)
            if match:
                params['query'] = match.group(1).strip()
        
        elif module == ModuleTarget.NEURAL_SEARCH:
            # Extract search query
            match = re.search(r'(?:search|find|look up)\s+(?:for\s+)?(.+?)(?:\s*$)', query, re.IGNORECASE)
            if match:
                params['query'] = match.group(1).strip()
        
        elif module == ModuleTarget.SCHEDULER:
            # Extract reminder text and time
            match = re.search(r'remind.*?\s+(.+?)(?:\s+at\s+|\s+in\s+|\s*$)', query, re.IGNORECASE)
            if match:
                params['text'] = match.group(1).strip()
            # Extract time
            time_match = re.search(r'at\s+(\d{1,2}:\d{2})', query, re.IGNORECASE)
            if time_match:
                params['time'] = time_match.group(1)
        
        elif module == ModuleTarget.BROWSER:
            # Extract URL
            url_match = re.search(r'https?://[^\s]+', query)
            if url_match:
                params['url'] = url_match.group(0)
        
        elif module == ModuleTarget.GLOBE:
            # Extract region/country filter
            match = re.search(r'(?:globe|filter|show)\s+(.+?)(?:\s*$)', query, re.IGNORECASE)
            if match:
                params['filter'] = match.group(1).strip()
        
        return params
    
    def get_stats(self) -> Dict[str, Any]:
        """Return router statistics."""
        return {
            "total_routed": self.total_routes,
            "layer1_hits": self.layer1_hits,
            "layer2_hits": self.layer2_hits,
            "layer3_hits": self.layer3_hits,
            "layer1_ratio": round(self.layer1_hits / max(self.total_routes, 1), 3),
            "layer2_ratio": round(self.layer2_hits / max(self.total_routes, 1), 3),
        }


# ── Singleton ──────────────────────────────────────────────────────────────────
intent_router = IntentRouter()


# ── Pydantic Models for API ────────────────────────────────────────────────────

class ContextInput(BaseModel):
    """Context object passed with routing request."""
    module: Optional[str] = None
    item_type: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    label: Optional[str] = None


class RoutingRequest(BaseModel):
    """Request to the routing endpoint."""
    query: str
    context: Optional[ContextInput] = None


class RoutingResponse(BaseModel):
    """Response from the routing endpoint."""
    target_module: str
    action: str
    parameters: Dict[str, Any]
    confidence: float
    reasoning: str
    enriched_query: str
    requires_llm: bool
