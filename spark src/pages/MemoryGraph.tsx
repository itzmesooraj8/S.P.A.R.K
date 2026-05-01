import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';

interface MemoryNode extends d3.SimulationNodeDatum {
  id: string;
  group: number;
  label: string;
  content?: string;
  radius: number;
}

interface MemoryLink extends d3.SimulationLinkDatum<MemoryNode> {
  source: string;
  target: string;
  value: number;
}

export default function MemoryGraph() {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [selectedNode, setSelectedNode] = useState<MemoryNode | null>(null);

  useEffect(() => {
    if (!svgRef.current || !containerRef.current) return;

    const width = containerRef.current.clientWidth;
    const height = containerRef.current.clientHeight;

    // Mock data for initial render until ChromaDB data is bridged
    const nodes: MemoryNode[] = [
      { id: "User", group: 1, label: "Sooraj", radius: 20 },
      { id: "S.P.A.R.K.", group: 1, label: "S.P.A.R.K.", radius: 20 },
      { id: "Project_Solo", group: 2, label: "Solo Leveling", radius: 15, content: "Discussed on Tuesday. Production build pending." },
      { id: "Concept_OODA", group: 3, label: "OODA Loop", radius: 15, content: "Core operating model: Observe, Orient, Decide, Act." },
      { id: "Asset_CUPID", group: 4, label: "CUPID (Stock)", radius: 10, content: "Bought 50 shares at 120." },
      { id: "Concept_Persona", group: 3, label: "Persona", radius: 10, content: "J.A.R.V.I.S. archetype. No apologies." },
    ];

    const links: MemoryLink[] = [
      { source: "User", target: "S.P.A.R.K.", value: 5 },
      { source: "User", target: "Project_Solo", value: 3 },
      { source: "S.P.A.R.K.", target: "Concept_OODA", value: 4 },
      { source: "S.P.A.R.K.", target: "Concept_Persona", value: 4 },
      { source: "User", target: "Asset_CUPID", value: 2 },
    ];

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    // Zoom setup
    const g = svg.append("g");
    svg.call(d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 4])
      .on("zoom", (event) => g.attr("transform", event.transform))
    );

    const simulation = d3.forceSimulation(nodes)
      .force("link", d3.forceLink<MemoryNode, MemoryLink>(links).id(d => d.id).distance(100))
      .force("charge", d3.forceManyBody().strength(-300))
      .force("center", d3.forceCenter(width / 2, height / 2));

    const link = g.append("g")
      .attr("stroke", "#00f5ff33")
      .attr("stroke-opacity", 0.6)
      .selectAll("line")
      .data(links)
      .join("line")
      .attr("stroke-width", d => Math.sqrt(d.value));

    const node = g.append("g")
      .attr("stroke", "#fff")
      .attr("stroke-width", 1.5)
      .selectAll("circle")
      .data(nodes)
      .join("circle")
      .attr("r", d => d.radius)
      .attr("fill", d => d.group === 1 ? "#00f5ff" : d.group === 2 ? "#ff2a2a" : "#ffb000")
      .on("click", (event, d) => setSelectedNode(d));

    // Glow filter
    const defs = svg.append("defs");
    const filter = defs.append("filter").attr("id", "glow");
    filter.append("feGaussianBlur").attr("stdDeviation", "2.5").attr("result", "coloredBlur");
    const feMerge = filter.append("feMerge");
    feMerge.append("feMergeNode").attr("in", "coloredBlur");
    feMerge.append("feMergeNode").attr("in", "SourceGraphic");
    node.attr("filter", "url(#glow)");

    const label = g.append("g")
      .selectAll("text")
      .data(nodes)
      .join("text")
      .text(d => d.label)
      .attr("font-size", "10px")
      .attr("font-family", "monospace")
      .attr("fill", "#fff")
      .attr("dx", 15)
      .attr("dy", 4)
      .attr("pointer-events", "none");

    simulation.on("tick", () => {
      link
        .attr("x1", d => (d.source as MemoryNode).x!)
        .attr("y1", d => (d.source as MemoryNode).y!)
        .attr("x2", d => (d.target as MemoryNode).x!)
        .attr("y2", d => (d.target as MemoryNode).y!);

      node
        .attr("cx", d => d.x!)
        .attr("cy", d => d.y!);

      label
        .attr("x", d => d.x!)
        .attr("y", d => d.y!);
    });

    return () => {
      simulation.stop();
    };
  }, []);

  return (
    <div className="w-full h-screen bg-[#010812] flex flex-col relative font-mono overflow-hidden">
      {/* Scan line effect */}
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.25)_50%),linear-gradient(90deg,rgba(255,0,0,0.06),rgba(0,255,0,0.06),rgba(0,0,255,0.06))] bg-[length:100%_4px,3px_100%] z-10 opacity-10" />

      <div className="absolute top-6 left-6 z-20 pointer-events-none">
        <h1 className="text-2xl font-bold uppercase tracking-[0.3em] neon-text-amber font-['Orbitron']">
          SEMANTIC MEMORY GRAPH
        </h1>
        <div className="text-amber-500/70 text-xs tracking-widest mt-1">ChromaDB Neural Map Visualization</div>
      </div>

      <div ref={containerRef} className="flex-1 w-full relative z-0">
        <svg ref={svgRef} className="w-full h-full" />
      </div>

      {/* Node details panel */}
      {selectedNode && (
        <div className="absolute top-24 right-6 w-[350px] hud-panel p-6 bg-[#000000cc] backdrop-blur-sm z-20 border-amber-500/50 pointer-events-auto">
          <div className="flex justify-between items-start mb-4 border-b border-amber-500/30 pb-2">
            <h2 className="text-amber-400 font-bold text-lg tracking-wider">{selectedNode.label}</h2>
            <button 
              className="text-gray-500 hover:text-white"
              onClick={() => setSelectedNode(null)}
            >
              [X]
            </button>
          </div>
          <div className="text-gray-300 text-sm leading-relaxed whitespace-pre-wrap">
            {selectedNode.content || "No detailed content stored for this memory node."}
          </div>
          <div className="mt-4 pt-2 border-t border-gray-800 flex justify-between text-[10px] text-gray-500">
            <span>ID: {selectedNode.id}</span>
            <span>CLUSTER: {selectedNode.group}</span>
          </div>
        </div>
      )}
    </div>
  );
}
