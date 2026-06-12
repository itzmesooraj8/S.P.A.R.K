'use client';

export default function AgentHealth({ agents }: { agents: any[] }) {
  return (
    <div className="spark-card">
      <h2 className="text-lg font-bold spark-accent mb-4">Agent Health</h2>
      <div className="space-y-3">
        {agents.map((agent, i) => (
          <div key={i} className="flex items-center justify-between p-3 rounded bg-gray-900">
            <div className="flex items-center gap-3">
              <span className={`status-dot ${agent.status === 'running' ? 'status-active pulse' : agent.status === 'idle' ? 'status-idle' : 'status-error'}`} />
              <span className="font-mono">{agent.name}</span>
            </div>
            <div className="flex items-center gap-4 text-sm text-gray-400">
              <span>Status: <span className={agent.status === 'running' ? 'spark-success' : ''}>{agent.status}</span></span>
              <span>Latency: {agent.latency_ms || 0}ms</span>
              <span>Errors: {agent.errors || 0}</span>
            </div>
          </div>
        ))}
        {agents.length === 0 && <div className="text-gray-500">No agents running</div>}
      </div>
    </div>
  );
}
