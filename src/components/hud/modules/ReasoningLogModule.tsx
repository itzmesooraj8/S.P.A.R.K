import { useState, useEffect } from 'react';
import { Terminal } from 'lucide-react';

const LOG_COLORS = ['#00f5ff', '#00ff88', '#ffb800', '#ff3b3b', '#8b00ff', '#0066ff'];
const REASONING_LINES = [
  [0, 'INIT: Loading semantic memory layer...'],
  [0, 'LOAD: Contextual embeddings: 4096 dims'],
  [1, 'OK: Knowledge graph ready (2.1M nodes)'],
  [2, 'THINK: Analyzing query intent...'],
  [0, 'RECALL: Fetching related concepts...'],
  [1, 'MATCH: Similarity score 0.94 — high confidence'],
  [2, 'PLAN: Generating response strategy...'],
  [3, 'WARN: Ambiguity detected in token 12'],
  [0, 'RESOLVE: Applying disambiguation rules'],
  [1, 'EVAL: Logical consistency check PASSED'],
  [0, 'GENERATE: Beam search k=4, temp=0.7'],
  [1, 'OUTPUT: Response compiled (312 tokens)'],
  [2, 'POST: Running safety filters...'],
  [1, 'OK: Response cleared for delivery'],
  [0, 'IDLE: Awaiting next input...'],
];

export default function ReasoningLogModule() {
  const [displayed, setDisplayed] = useState<typeof REASONING_LINES>([]);
  const [idx, setIdx] = useState(0);

  useEffect(() => {
    const t = setInterval(() => {
      if (idx < REASONING_LINES.length) {
        setDisplayed(p => [...p, REASONING_LINES[idx]]);
        setIdx(i => i + 1);
      } else {
        setTimeout(() => { setDisplayed([]); setIdx(0); }, 2000);
      }
    }, 350);
    return () => clearInterval(t);
  }, [idx]);

  return (
    <div className="flex flex-col gap-3 p-4 h-full">
      <div className="flex items-center gap-2 pb-2 border-b border-hud-cyan/20">
        <Terminal size={14} className="text-hud-cyan" />
        <span className="font-orbitron text-xs tracking-widest neon-text">AI REASONING LOG</span>
        <div className="ml-auto w-1.5 h-1.5 rounded-full bg-hud-green animate-pulse" />
      </div>
      <div className="flex-1 bg-black/60 rounded border border-hud-cyan/15 p-3 overflow-y-auto scrollbar-hud">
        <div className="font-mono-tech text-[9px] text-hud-green mb-2">SPARK-7B REASONING ENGINE v4.1</div>
        <div className="font-mono-tech text-[9px] text-hud-cyan/40 mb-3">{'>'} Session started {new Date().toLocaleTimeString()}</div>
        {displayed.map((line, i) => (
          <div key={i} className="flex gap-2 leading-5">
            <span className="text-hud-cyan/30 shrink-0">{(i * 0.35).toFixed(2)}s</span>
            <span style={{ color: LOG_COLORS[line[0] as number] }}>{line[1] as string}</span>
          </div>
        ))}
        <span className="font-mono-tech text-[9px] text-hud-cyan/50 animate-type-cursor">█</span>
      </div>
    </div>
  );
}
