"""
SPARK API Contract Models — Pydantic definitions.

Mirrors src/types/contracts.ts exactly.  When you change a field here,
update the TS file too (and bump API_SCHEMA_VERSION in __init__.py).

Schema v1 — 2026-03-01
"""

from __future__ import annotations
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field


# ──────────────────────────────────────────────────────────────────────────────
# ENVELOPE — every WebSocket frame is wrapped in this
# ──────────────────────────────────────────────────────────────────────────────

class WsEnvelope(BaseModel):
    """Top-level wrapper for all WebSocket messages (both directions)."""
    v: int = 1                        # schema version
    type: str                         # discriminator
    ts: Optional[float] = None        # unix ms timestamp (server fills on send)


# ──────────────────────────────────────────────────────────────────────────────
# /ws/ai  — AI chat channel
# ──────────────────────────────────────────────────────────────────────────────

class AiUserMessage(WsEnvelope):
    """Client → Server: text prompt from the user."""
    type: Literal["USER_INPUT"] = "USER_INPUT"
    content: str
    session_id: Optional[str] = None

class AiCancelMessage(WsEnvelope):
    """Client → Server: cancel current generation."""
    type: Literal["CANCEL"] = "CANCEL"
    session_id: Optional[str] = None

class AiTokenMessage(WsEnvelope):
    """Server → Client: one streamed token."""
    type: Literal["TOKEN"] = "TOKEN"
    token: str
    session_id: Optional[str] = None

class AiDoneMessage(WsEnvelope):
    """Server → Client: stream finished."""
    type: Literal["DONE"] = "DONE"
    session_id: Optional[str] = None

class AiToolExecuteMessage(WsEnvelope):
    """Server → Client: tool about to be called (for HUD reflection)."""
    type: Literal["TOOL_EXECUTE"] = "TOOL_EXECUTE"
    tool: str
    arguments: Dict[str, Any] = {}

class AiToolResultMessage(WsEnvelope):
    """Server → Client: tool execution result."""
    type: Literal["TOOL_RESULT"] = "TOOL_RESULT"
    tool: str
    status: Literal["completed", "failed"]
    output: Optional[Any] = None
    error: Optional[str] = None

class AiConfirmToolMessage(WsEnvelope):
    """Server → Client (via /ws/system): user must confirm a risky tool."""
    type: Literal["CONFIRM_TOOL"] = "CONFIRM_TOOL"
    tool: str
    arguments: Dict[str, Any] = {}
    risk_level: str = "HIGH"

class AiErrorMessage(WsEnvelope):
    """Server → Client: error response."""
    type: Literal["ERROR"] = "ERROR"
    message: str
    code: Optional[str] = None

# Union type consumed by frontend
AiServerMessage = Union[
    AiTokenMessage,
    AiDoneMessage,
    AiToolExecuteMessage,
    AiToolResultMessage,
    AiConfirmToolMessage,
    AiErrorMessage,
]


# ──────────────────────────────────────────────────────────────────────────────
# /ws/system  — telemetry & alerts channel
# ──────────────────────────────────────────────────────────────────────────────

class NetIo(BaseModel):
    bytes_sent: int = 0
    bytes_recv: int = 0

class GpuStats(BaseModel):
    load: float = 0.0
    memory_used: float = 0.0
    temperature: float = 0.0

class SystemMetrics(BaseModel):
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    disk_usage: float = 0.0
    net_io: NetIo = Field(default_factory=NetIo)
    gpu_stats: Optional[GpuStats] = None
    uptime_s: Optional[float] = None
    process_count: Optional[int] = None
    ping_ms: Optional[float] = None

class SystemStateUpdateMessage(WsEnvelope):
    """Server → Client: periodic telemetry snapshot."""
    type: Literal["STATE_UPDATE"] = "STATE_UPDATE"
    state: Dict[str, Any]   # includes 'metrics' key with SystemMetrics structure

class SystemAlertMessage(WsEnvelope):
    """Server → Client: cognitive loop alert or anomaly."""
    type: Literal["ALERT"] = "ALERT"
    severity: Literal["info", "warning", "critical"] = "info"
    title: str
    body: str
    source: Optional[str] = None

class SystemPingMessage(WsEnvelope):
    """Client → Server keep-alive."""
    type: Literal["PING"] = "PING"

class SystemPongMessage(WsEnvelope):
    """Server → Client keep-alive reply."""
    type: Literal["PONG"] = "PONG"

SystemServerMessage = Union[
    SystemStateUpdateMessage,
    SystemAlertMessage,
    SystemPongMessage,
]


# ──────────────────────────────────────────────────────────────────────────────
# /ws/globe  — globe intelligence push channel
# ──────────────────────────────────────────────────────────────────────────────

class GlobeEventItem(BaseModel):
    id: str
    lat: float
    lng: float
    type: str
    magnitude: Optional[float] = None
    title: Optional[str] = None
    severity: Optional[str] = None
    timestamp: Optional[float] = None
    extra: Dict[str, Any] = {}

class GlobeDeltaMessage(WsEnvelope):
    """Server → Client: incremental layer update."""
    type: Literal["GLOBE_DELTA"] = "GLOBE_DELTA"
    layer: str                       # e.g. "earthquake", "conflict", "fires"
    events: List[GlobeEventItem] = []

class GlobeTickerItem(BaseModel):
    symbol: str
    price: float
    change_pct: float
    volume: Optional[float] = None

class GlobeTickerMessage(WsEnvelope):
    """Server → Client: market ticker update."""
    type: Literal["GLOBE_TICKER"] = "GLOBE_TICKER"
    tickers: List[GlobeTickerItem] = []

class GlobeFusionAlert(BaseModel):
    id: str
    title: str
    risk_score: float
    layers_involved: List[str] = []
    region: Optional[str] = None
    timestamp: float

class GlobeFusionMessage(WsEnvelope):
    """Server → Client: signal fusion correlation alert."""
    type: Literal["GLOBE_FUSION"] = "GLOBE_FUSION"
    alerts: List[GlobeFusionAlert] = []

class GlobeHealthMessage(WsEnvelope):
    """Server → Client: provider circuit-breaker health summary."""
    type: Literal["GLOBE_HEALTH"] = "GLOBE_HEALTH"
    providers: Dict[str, Any] = {}

GlobeServerMessage = Union[
    GlobeDeltaMessage,
    GlobeTickerMessage,
    GlobeFusionMessage,
    GlobeHealthMessage,
]


# ──────────────────────────────────────────────────────────────────────────────
# REST — shared request/response shapes
# ──────────────────────────────────────────────────────────────────────────────

class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 3600

class ToolDefinition(BaseModel):
    name: str
    description: str
    risk_level: str
    parameters: Dict[str, Any] = {}

class ToolListResponse(BaseModel):
    tools: List[ToolDefinition]
    count: int

class CaseItem(BaseModel):
    """A saved user case/incident from the Globe drawer."""
    id: Optional[str] = None
    title: str
    description: str = ""
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    lat: Optional[float] = None
    lng: Optional[float] = None
    layer: Optional[str] = None
    tags: List[str] = []
    created_at: Optional[float] = None
    updated_at: Optional[float] = None
    meta: Dict[str, Any] = {}

class CaseListResponse(BaseModel):
    cases: List[CaseItem]
    total: int
