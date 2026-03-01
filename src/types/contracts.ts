/**
 * SPARK API Contract Types — TypeScript mirror of spark_core/contracts/models.py
 * Schema v1 — 2026-03-01
 *
 * When you change a field here, update the Python counterpart and bump
 * API_SCHEMA_VERSION in spark_core/contracts/__init__.py.
 */

// ─── Envelope ────────────────────────────────────────────────────────────────

export interface WsEnvelope {
    v: number;       // schema version (always 1 for now)
    type: string;    // discriminator
    ts?: number;     // unix-ms timestamp added by server
}

// ─── /ws/ai — AI chat channel ─────────────────────────────────────────────

/** Client → Server */
export interface AiUserMessage extends WsEnvelope {
    type: "USER_INPUT";
    content: string;
    session_id?: string;
}
export interface AiCancelMessage extends WsEnvelope {
    type: "CANCEL";
    session_id?: string;
}

/** Server → Client */
export interface AiTokenMessage extends WsEnvelope {
    type: "TOKEN";
    token: string;
    session_id?: string;
}
export interface AiDoneMessage extends WsEnvelope {
    type: "DONE";
    session_id?: string;
}
export interface AiToolExecuteMessage extends WsEnvelope {
    type: "TOOL_EXECUTE";
    tool: string;
    arguments: Record<string, unknown>;
}
export interface AiToolResultMessage extends WsEnvelope {
    type: "TOOL_RESULT";
    tool: string;
    status: "completed" | "failed";
    output?: unknown;
    error?: string;
}
export interface AiConfirmToolMessage extends WsEnvelope {
    type: "CONFIRM_TOOL";
    tool: string;
    arguments: Record<string, unknown>;
    risk_level: string;
}
export interface AiErrorMessage extends WsEnvelope {
    type: "ERROR";
    message: string;
    code?: string;
}

export type AiServerMessage =
    | AiTokenMessage
    | AiDoneMessage
    | AiToolExecuteMessage
    | AiToolResultMessage
    | AiConfirmToolMessage
    | AiErrorMessage;

/** @deprecated Use AiServerMessage — kept for back-compat */
export interface AiWsMessage {
    type: "response_token" | "response_done" | "tool_execute" | "tool_result" | "error" | "status" | "TOKEN" | "DONE";
    content?: string;
    token?: string;
    tool?: string;
    name?: string;
    arguments?: Record<string, unknown>;
    status?: "running" | "completed" | "failed";
    output?: unknown;
    done?: boolean;
}

// ─── /ws/system — telemetry & alerts channel ───────────────────────────────

export interface NetIo {
    bytes_sent: number;
    bytes_recv: number;
}
export interface GpuStats {
    load: number;
    memory_used: number;
    temperature: number;
}
export interface SystemMetrics {
    cpu_percent: number;
    memory_percent: number;
    disk_usage: number;
    net_io: NetIo;
    gpu_stats?: GpuStats;
    uptime_s?: number;
    process_count?: number;
    ping_ms?: number;
}

export interface SystemStateUpdateMessage extends WsEnvelope {
    type: "STATE_UPDATE";
    state: { metrics?: SystemMetrics } & Record<string, unknown>;
}
export interface SystemAlertMessage extends WsEnvelope {
    type: "ALERT";
    severity: "info" | "warning" | "critical";
    title: string;
    body: string;
    source?: string;
}
export interface SystemPingMessage extends WsEnvelope { type: "PING"; }
export interface SystemPongMessage extends WsEnvelope { type: "PONG"; }

export type SystemWsMessage =
    | SystemStateUpdateMessage
    | SystemAlertMessage
    | SystemPongMessage;

// ─── /ws/globe — globe intelligence push channel ────────────────────────────

export interface GlobeEventItem {
    id: string;
    lat: number;
    lng: number;
    type: string;
    magnitude?: number;
    title?: string;
    severity?: string;
    timestamp?: number;
    extra?: Record<string, unknown>;
}
export interface GlobeDeltaMessage extends WsEnvelope {
    type: "GLOBE_DELTA";
    layer: string;
    events: GlobeEventItem[];
}
export interface GlobeTickerItem {
    symbol: string;
    price: number;
    change_pct: number;
    volume?: number;
}
export interface GlobeTickerMessage extends WsEnvelope {
    type: "GLOBE_TICKER";
    tickers: GlobeTickerItem[];
}
export interface GlobeFusionAlert {
    id: string;
    title: string;
    risk_score: number;
    layers_involved: string[];
    region?: string;
    timestamp: number;
}
export interface GlobeFusionMessage extends WsEnvelope {
    type: "GLOBE_FUSION";
    alerts: GlobeFusionAlert[];
}
export interface GlobeHealthMessage extends WsEnvelope {
    type: "GLOBE_HEALTH";
    providers: Record<string, unknown>;
}
export type GlobeServerMessage =
    | GlobeDeltaMessage
    | GlobeTickerMessage
    | GlobeFusionMessage
    | GlobeHealthMessage;

// ─── REST shared shapes ──────────────────────────────────────────────────────

export interface TokenPairResponse {
    access_token: string;
    refresh_token: string;
    token_type: string;
    expires_in: number;
}

export interface ToolDefinition {
    name: string;
    description: string;
    risk_level: string;
    parameters: Record<string, unknown>;
}
export interface ToolListResponse {
    tools: ToolDefinition[];
    count: number;
}

export interface CaseItem {
    id?: string;
    title: string;
    description?: string;
    severity: "low" | "medium" | "high" | "critical";
    lat?: number;
    lng?: number;
    layer?: string;
    tags: string[];
    created_at?: number;
    updated_at?: number;
    meta?: Record<string, unknown>;
}
export interface CaseListResponse {
    cases: CaseItem[];
    total: number;
}

// ─── ToolEvent (internal HUD tracking) ───────────────────────────────────────

export interface ToolEvent {
    tool: string;
    arguments: Record<string, unknown>;
    status: "running" | "completed" | "failed";
    output?: unknown;
    timestamp: number;
}

// ─── AuditResult ─────────────────────────────────────────────────────────────

export interface AuditResult {
    status: "success" | "error";
    reason?: string;
    issues?: string[];
    score?: number;
}
