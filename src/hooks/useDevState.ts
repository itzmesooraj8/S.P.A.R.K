import { useState, useEffect, useRef } from 'react';

export interface CodeNode {
    id: string;
    type: string;
    path: string;
    signature: string;
    start_line: number;
    end_line: number;
}

export interface CodeEdge {
    source: string;
    target: string;
    relation: string;
}

export interface CodeGraph {
    nodes: CodeNode[];
    edges: CodeEdge[];
}

export interface ContextMap {
    node_to_tests: Record<string, string[]>;
    test_to_nodes: Record<string, string[]>;
}

export interface MutationLogEntry {
    timestamp: number;
    target_node: string;
    patch_hash: string;
    patch_content: string;
    success: boolean;
    duration_ms: number;
    test_passed: number;
    test_failed: number;
    test_total: number;
    error_trace?: string;
}

export interface DevState {
    version: number;
    code_graph: CodeGraph;
    context_map: ContextMap;
    mutation_log: MutationLogEntry[];
    sandbox_state: {
        is_running: boolean;
        last_cmd: string;
        cmd_active: boolean;
    };
    project_focus?: string;
    history?: any; // Added based on update logic
    [key: string]: any;
}

export function useDevState(): DevState {
    const [devState, setDevState] = useState<DevState>({
        version: 0,
        code_graph: { nodes: [], edges: [] },
        context_map: { node_to_tests: {}, test_to_nodes: {} },
        mutation_log: [],
        sandbox_state: {
            is_running: false,
            last_cmd: '',
            cmd_active: false
        },
        project_focus: undefined,
        history: undefined // Initialized history
    });

    useEffect(() => {
        let ws: WebSocket;
        let reconnectTimeout: NodeJS.Timeout;

        const connect = () => {
            ws = new WebSocket("ws://localhost:8000/ws/system");

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);

                    if (data.type === "STATE_UPDATE" && data.state && typeof data.version === 'number') {
                        setDevState(prev => {
                            if (data.version <= prev.version) {
                                return prev; // Ignore stale frames
                            }
                            return {
                                ...prev,
                                version: data.version,
                                code_graph: data.state.code_graph || prev.code_graph,
                                context_map: data.state.context_map || prev.context_map,
                                mutation_log: data.state.mutation_log || prev.mutation_log,
                                history: data.state.history || prev.history,
                                sandbox_state: data.state.sandbox_state || prev.sandbox_state,
                                project_focus: data.state.project_focus || prev.project_focus
                            };
                        });
                    }
                } catch (error) {
                    console.error("[useDevState] Failed to parse payload:", error);
                }
            };

            ws.onclose = () => {
                reconnectTimeout = setTimeout(connect, 2000);
            };

            ws.onerror = (error) => {
                ws.close();
            };
        };

        connect();

        return () => {
            clearTimeout(reconnectTimeout);
            if (ws) {
                ws.close();
            }
        };
    }, []);

    return devState;
}
