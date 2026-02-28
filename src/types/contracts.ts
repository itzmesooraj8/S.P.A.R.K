export interface AiWsMessage {
    type: "response_token" | "response_done" | "tool_execute" | "tool_result" | "error" | "status";
    content?: string;
    token?: string;
    tool?: string;
    name?: string;
    arguments?: Record<string, any>;
    status?: "running" | "completed" | "failed";
    output?: any;
    done?: boolean;
}

export interface SystemWsMessage {
    type: "metrics" | "alert" | "status" | "audit_update" | "workspace_graph_summary";
    data: SystemMetrics | any;
}

export interface ToolEvent {
    tool: string;
    arguments: Record<string, any>;
    status: "running" | "completed" | "failed";
    output?: any;
    timestamp: number;
}

export interface SystemMetrics {
    cpu_percent: number;
    memory_percent: number;
    disk_usage: number;
    net_io: {
        bytes_sent: number;
        bytes_recv: number;
    };
    gpu_stats?: {
        load: number;
        memory_used: number;
        temperature: number;
    };
}

export interface AuditResult {
    status: "success" | "error";
    reason?: string;
    issues?: string[];
    score?: number;
}

export interface ToolDefinition {
    name: string;
    description: string;
    parameters: Record<string, any>;
}
