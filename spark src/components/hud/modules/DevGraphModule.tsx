import { useMemo, useState } from 'react';
import { ReactFlow, Background, Controls, Node, Edge as FlowEdge, MarkerType } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { useDevState } from '@/hooks/useDevState';
import { Brain, FileCode, CheckCircle, AlertTriangle, Clock } from 'lucide-react';

export default function DevGraphModule() {
    const { code_graph, context_map, mutation_log } = useDevState();
    const [selectedNode, setSelectedNode] = useState<string | null>(null);

    // Group nodes by module to layout roughly
    const moduleMap = useMemo(() => {
        const map = new Map<string, string[]>();
        (code_graph.nodes || []).forEach(n => {
            if (!map.has(n.path)) map.set(n.path, []);
            map.get(n.path)!.push(n.id);
        });
        return map;
    }, [code_graph]);

    // Translate code CodeNodes into ReactFlow nodes
    const nodes: Node[] = useMemo(() => {
        const flowNodes: Node[] = [];
        let xOffset = 0;

        // A simple grid layout by module
        Array.from(moduleMap.entries()).forEach(([path, nodeIds], modIdx) => {
            flowNodes.push({
                id: `module_${path}`,
                type: 'group',
                position: { x: xOffset, y: 0 },
                data: { label: path },
                style: { width: 300, height: 100 + nodeIds.length * 80, backgroundColor: 'rgba(0,255,255,0.02)', border: '1px solid rgba(0,255,255,0.1)' }
            });

            nodeIds.forEach((id, idx) => {
                // Calculate risk/failures from log
                const failures = (mutation_log || []).filter(ml => ml.target_node === id && !ml.success).length;
                const total = (mutation_log || []).filter(ml => ml.target_node === id).length;
                const failureColor = failures > 2 ? '#ff3b3b' : failures > 0 ? '#ffb800' : '#00f5ff';

                // Get test coverage
                const tests = (context_map.node_to_tests || {})[id] || [];
                const testCount = tests.length;

                flowNodes.push({
                    id,
                    position: { x: 20, y: 40 + idx * 80 },
                    parentId: `module_${path}`,
                    extent: 'parent',
                    data: { label: id.split('.').pop(), tests: testCount, totalMutations: total, failures },
                    style: {
                        background: 'rgba(0,10,20,0.8)',
                        border: `1px solid ${failureColor}`,
                        color: '#fff',
                        borderRadius: '4px',
                        fontSize: '10px',
                        fontFamily: 'monospace',
                        padding: '8px'
                    }
                });
            });

            xOffset += 350;
        });

        return flowNodes;
    }, [moduleMap, context_map, mutation_log]);

    const edges: FlowEdge[] = useMemo(() => {
        return (code_graph.edges || []).map((e, idx) => ({
            id: `e_${e.source}_${e.target}_${idx}`,
            source: e.source,
            target: e.target,
            label: e.relation,
            animated: true,
            style: { stroke: '#00f5ff', strokeWidth: 1.5, opacity: 0.5 },
            markerEnd: { type: MarkerType.ArrowClosed, color: '#00f5ff' }
        }));
    }, [code_graph]);

    const onNodeClick = (_: any, node: Node) => {
        if (node.id && !node.id.startsWith('module_')) {
            setSelectedNode(node.id);
        } else {
            setSelectedNode(null);
        }
    };

    const selectedNodeData = useMemo(() => {
        if (!selectedNode) return null;
        const n = code_graph.nodes?.find(x => x.id === selectedNode);
        const m = (mutation_log || []).filter(x => x.target_node === selectedNode).reverse();
        const tests = (context_map.node_to_tests || {})[selectedNode] || [];
        return { n, mutations: m, tests };
    }, [selectedNode, code_graph, mutation_log, context_map]);

    return (
        <div className="flex w-full h-full text-white bg-black/80 font-mono-tech">
            <div className="flex-1 relative border-r border-hud-cyan/20">
                <ReactFlow nodes={nodes} edges={edges} onNodeClick={onNodeClick} fitView>
                    <Background color="#00f5ff" style={{ opacity: 0.1 }} />
                    <Controls className="!bg-black/50 !text-hud-cyan !border-hud-cyan/30" />
                </ReactFlow>
                <div className="absolute top-2 left-2 bg-black/60 p-2 border border-hud-cyan/30 rounded text-[10px] text-hud-cyan z-10">
                    <div className="flex items-center gap-1"><Brain size={12} /> SPARK STRUCTURAL COGNITION</div>
                    <div className="mt-1 opacity-70">Nodes: {code_graph.nodes?.length || 0} | Edges: {code_graph.edges?.length || 0}</div>
                </div>
            </div>

            <div className="w-80 flex flex-col p-2 bg-black/40 overflow-hidden">
                <div className="border-b border-hud-cyan/20 pb-2 mb-2 shrink-0">
                    <h2 className="text-hud-cyan font-bold flex items-center gap-2">
                        <FileCode size={16} /> NODE INSPECTOR
                    </h2>
                </div>

                <div className="flex-1 overflow-y-auto pr-1 scrollbar-hud text-xs">
                    {!selectedNodeData ? (
                        <div className="text-hud-cyan/40 text-center mt-10">Click a node to inspect its architectural context and telemetry.</div>
                    ) : (
                        <div className="flex flex-col gap-3">
                            <div className="bg-hud-cyan/10 border border-hud-cyan/20 p-2 rounded break-all">
                                <span className="text-hud-cyan/60 ml-1">ID:</span> <span className="text-hud-cyan">{selectedNode}</span><br />
                                <span className="text-hud-cyan/60 ml-1">TYPE:</span> <span className="text-hud-cyan">{selectedNodeData.n?.type}</span><br />
                                <span className="text-hud-cyan/60 ml-1">FILE:</span> <span className="text-hud-cyan">{selectedNodeData.n?.path}</span><br />
                                <span className="text-hud-cyan/60 ml-1">LINES:</span> <span className="text-hud-cyan">{selectedNodeData.n?.start_line} - {selectedNodeData.n?.end_line}</span>
                            </div>

                            <div>
                                <div className="font-bold text-hud-cyan/70 border-b border-hud-cyan/20 mb-1 pb-1 flex justify-between">
                                    <span>TEST COVERAGE ({selectedNodeData.tests.length})</span>
                                </div>
                                {selectedNodeData.tests.length === 0 ? <div className="text-hud-red/50">Uncovered Node</div> : (
                                    <ul className="list-disc pl-4 text-[10px] text-hud-green flex flex-col gap-0.5 mt-1 opacity-80">
                                        {selectedNodeData.tests.map((t, idx) => <li key={idx} className="break-all">{t}</li>)}
                                    </ul>
                                )}
                            </div>

                            <div className="flex-1">
                                <div className="font-bold text-hud-cyan/70 border-b border-hud-cyan/20 mb-1 pb-1">MUTATION TIMELINE</div>
                                {selectedNodeData.mutations.length === 0 ? (
                                    <div className="text-hud-cyan/40">No historical mutations.</div>
                                ) : (
                                    <div className="flex flex-col gap-2 mt-2">
                                        {selectedNodeData.mutations.map((m, idx) => (
                                            <div key={idx} className={`p-2 rounded border ${m.success ? 'border-hud-green/30 bg-hud-green/5' : 'border-hud-red/30 bg-hud-red/5'}`}>
                                                <div className="flex items-center justify-between mb-1">
                                                    <span className={`flex items-center gap-1 font-bold ${m.success ? 'text-hud-green' : 'text-hud-red'}`}>
                                                        {m.success ? <CheckCircle size={10} /> : <AlertTriangle size={10} />}
                                                        {m.success ? 'APPLIED' : 'ROLLED BACK'}
                                                    </span>
                                                    <span className="flex items-center gap-1 text-[9px] text-hud-cyan/60">
                                                        <Clock size={8} /> {new Date(m.timestamp * 1000).toLocaleTimeString()}
                                                    </span>
                                                </div>
                                                <div className="text-[9px] text-hud-cyan/80">
                                                    {m.test_passed}✓ {m.test_failed}✗ ({m.duration_ms}ms)
                                                </div>
                                                {!m.success && m.error_trace && (
                                                    <div className="mt-1 bg-black/50 p-1 text-hud-red/70 text-[9px] font-mono break-all whitespace-pre-wrap max-h-24 overflow-y-auto scrollbar-hud">
                                                        {m.error_trace.split('\n')[0]} {/* First line of trace */}
                                                    </div>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
