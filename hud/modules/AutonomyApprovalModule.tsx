import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { CheckCircle2, RefreshCw, XCircle, Wand2, Puzzle, FileCode } from 'lucide-react';
import { apiGet, apiPost } from '@/lib/api';

type PromptReview = {
  id: string;
  created_at: string;
  summary: string;
  system_addendum: string;
  tool_notes: Record<string, string>;
  signals: Record<string, number>;
  status: string;
};

type ToolReview = {
  id: string;
  created_at: string;
  name: string;
  description: string;
  code: string;
  status: string;
  path: string;
};

type ReviewPayload = {
  prompt_state: Record<string, unknown>;
  prompts: PromptReview[];
  tools: ToolReview[];
};

function CodeBlock({ text }: { text: string }) {
  return <pre className="max-h-40 overflow-y-auto rounded border border-hud-cyan/15 bg-black/40 p-2 font-mono-tech text-[8px] text-hud-cyan/60 whitespace-pre-wrap">{text}</pre>;
}

function PromptCard({ review, onApprove, onReject }: { review: PromptReview; onApprove: (id: string) => void; onReject: (id: string) => void; }) {
  return (
    <div className="hud-panel rounded p-3 flex flex-col gap-2 border-hud-cyan/15">
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="font-orbitron text-[10px] text-hud-cyan">PROMPT REVIEW</div>
          <div className="font-mono-tech text-[8px] text-hud-cyan/40">{review.id}</div>
        </div>
        <div className="font-mono-tech text-[7px] text-hud-amber/70">{new Date(review.created_at).toLocaleString()}</div>
      </div>
      <div className="font-mono-tech text-[9px] text-hud-cyan/70">{review.summary}</div>
      {review.system_addendum && <CodeBlock text={review.system_addendum} />}
      {Object.keys(review.tool_notes || {}).length > 0 && <CodeBlock text={JSON.stringify(review.tool_notes, null, 2)} />}
      <div className="flex gap-2 justify-end">
        <button onClick={() => onReject(review.id)} className="flex items-center gap-1 rounded border border-hud-red/30 px-2 py-1 font-orbitron text-[8px] text-hud-red/70 hover:border-hud-red/60">
          <XCircle size={10} /> REJECT
        </button>
        <button onClick={() => onApprove(review.id)} className="flex items-center gap-1 rounded border border-hud-green/30 px-2 py-1 font-orbitron text-[8px] text-hud-green/70 hover:border-hud-green/60">
          <CheckCircle2 size={10} /> APPROVE
        </button>
      </div>
    </div>
  );
}

function ToolCard({ review, onApprove, onReject }: { review: ToolReview; onApprove: (id: string) => void; onReject: (id: string) => void; }) {
  return (
    <div className="hud-panel rounded p-3 flex flex-col gap-2 border-hud-purple/20">
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="font-orbitron text-[10px] text-hud-purple">TOOL REVIEW</div>
          <div className="font-mono-tech text-[8px] text-hud-cyan/40">{review.name}</div>
        </div>
        <div className="font-mono-tech text-[7px] text-hud-amber/70">{new Date(review.created_at).toLocaleString()}</div>
      </div>
      <div className="font-mono-tech text-[9px] text-hud-cyan/70">{review.description || 'Generated tool pending approval.'}</div>
      <CodeBlock text={review.code} />
      <div className="flex gap-2 justify-end">
        <button onClick={() => onReject(review.id)} className="flex items-center gap-1 rounded border border-hud-red/30 px-2 py-1 font-orbitron text-[8px] text-hud-red/70 hover:border-hud-red/60">
          <XCircle size={10} /> REJECT
        </button>
        <button onClick={() => onApprove(review.id)} className="flex items-center gap-1 rounded border border-hud-green/30 px-2 py-1 font-orbitron text-[8px] text-hud-green/70 hover:border-hud-green/60">
          <CheckCircle2 size={10} /> APPROVE
        </button>
      </div>
    </div>
  );
}

export default function AutonomyApprovalModule() {
  const { data, isLoading, refetch } = useQuery<ReviewPayload>({
    queryKey: ['autonomy-reviews'],
    queryFn: () => apiGet<ReviewPayload>('/api/runtime/autonomy/reviews'),
    refetchInterval: 3000,
    retry: false,
  });

  const promptCount = data?.prompts?.length ?? 0;
  const toolCount = data?.tools?.length ?? 0;

  const approvePrompt = async (id: string) => { await apiPost(`/api/runtime/autonomy/prompts/${id}/approve`, {}); await refetch(); };
  const rejectPrompt = async (id: string) => { await apiPost(`/api/runtime/autonomy/prompts/${id}/reject`, {}); await refetch(); };
  const approveTool = async (id: string) => { await apiPost(`/api/runtime/autonomy/tools/${id}/approve`, {}); await refetch(); };
  const rejectTool = async (id: string) => { await apiPost(`/api/runtime/autonomy/tools/${id}/reject`, {}); await refetch(); };

  const statusSummary = useMemo(() => `Prompts ${promptCount} · Tools ${toolCount}`, [promptCount, toolCount]);

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <div className="border-b border-hud-cyan/20 px-4 py-3">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Wand2 size={14} className="text-hud-amber" />
            <span className="font-orbitron text-xs tracking-widest neon-text">AUTONOMY REVIEW</span>
          </div>
          <button onClick={() => refetch()} className="flex items-center gap-1 rounded border border-hud-cyan/20 px-2 py-1 font-orbitron text-[8px] text-hud-cyan/60 hover:text-hud-cyan">
            <RefreshCw size={10} className={isLoading ? 'animate-spin' : ''} /> REFRESH
          </button>
        </div>
        <div className="mt-2 font-mono-tech text-[9px] text-hud-cyan/50">{statusSummary}</div>
      </div>

      <div className="flex-1 overflow-y-auto scrollbar-hud p-3 flex flex-col gap-3">
        {promptCount === 0 && toolCount === 0 ? (
          <div className="flex h-40 items-center justify-center rounded border border-hud-cyan/10 bg-black/20 text-hud-cyan/40 font-orbitron text-[9px]">
            No pending prompt or tool reviews.
          </div>
        ) : null}

        {promptCount > 0 && (
          <section className="flex flex-col gap-2">
            <div className="flex items-center gap-2 font-orbitron text-[9px] text-hud-cyan/60"><FileCode size={11} /> LAYER 2 · PROMPTS</div>
            {data?.prompts?.map(review => (
              <PromptCard key={review.id} review={review} onApprove={approvePrompt} onReject={rejectPrompt} />
            ))}
          </section>
        )}

        {toolCount > 0 && (
          <section className="flex flex-col gap-2">
            <div className="flex items-center gap-2 font-orbitron text-[9px] text-hud-purple/70"><Puzzle size={11} /> LAYER 3 · TOOLS</div>
            {data?.tools?.map(review => (
              <ToolCard key={review.id} review={review} onApprove={approveTool} onReject={rejectTool} />
            ))}
          </section>
        )}
      </div>
    </div>
  );
}