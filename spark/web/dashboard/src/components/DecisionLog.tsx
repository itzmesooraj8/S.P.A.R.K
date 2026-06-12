'use client';

export default function DecisionLog({ decisions }: { decisions: any[] }) {
  return (
    <div className="spark-card">
      <h2 className="text-lg font-bold spark-accent mb-4">Decision Log</h2>
      <div className="space-y-2 max-h-96 overflow-y-auto">
        {decisions.map((d, i) => (
          <div key={i} className="p-3 rounded bg-gray-900 text-sm">
            <div className="flex items-center gap-3 mb-1">
              <span className="text-gray-500 font-mono text-xs">
                {new Date(d.timestamp * 1000).toLocaleTimeString()}
              </span>
              <span className="font-bold spark-accent">{d.action}</span>
              <span className={`px-2 py-0.5 rounded text-xs ${
                d.outcome === 'success' ? 'bg-green-900 text-green-300' :
                d.outcome === 'failed' ? 'bg-red-900 text-red-300' :
                'bg-gray-800 text-gray-300'
              }`}>
                {d.outcome}
              </span>
            </div>
            <div className="text-gray-400">{d.reason}</div>
            {d.alternatives?.length > 0 && (
              <div className="text-gray-500 text-xs mt-1">Alternatives: {d.alternatives.join(', ')}</div>
            )}
          </div>
        ))}
        {decisions.length === 0 && <div className="text-gray-500">No decisions recorded</div>}
      </div>
    </div>
  );
}
