'use client';

export default function MemoryExplorer({ stats, working }: { stats: any; working: any }) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <div className="spark-card">
        <h2 className="text-lg font-bold spark-accent mb-4">Long-Term Memory</h2>
        <div className="space-y-3">
          <div className="flex justify-between p-3 rounded bg-gray-900">
            <span>Semantic (Facts & Knowledge)</span>
            <span className="spark-accent">{stats?.semantic_count || 0}</span>
          </div>
          <div className="flex justify-between p-3 rounded bg-gray-900">
            <span>Episodic (Conversations)</span>
            <span className="spark-accent">{stats?.episodic_count || 0}</span>
          </div>
          <div className="flex justify-between p-3 rounded bg-gray-900">
            <span>Procedural (Skills)</span>
            <span className="spark-accent">{stats?.procedural_count || 0}</span>
          </div>
        </div>
      </div>

      <div className="spark-card">
        <h2 className="text-lg font-bold spark-accent mb-4">Working Memory</h2>
        <div className="space-y-2 text-sm">
          <div><span className="text-gray-400">Objective:</span> {working?.objective?.description || 'None'}</div>
          <div><span className="text-gray-400">Current Task:</span> {working?.task?.description || 'idle'}</div>
          <div><span className="text-gray-400">Active Window:</span> {working?.context?.current_window || '?'}</div>
          <div><span className="text-gray-400">Attention Focus:</span> {working?.attention?.focus || 'none'}</div>
          <div><span className="text-gray-400">Conversation Buffer:</span> {working?.conversation_length || 0} turns</div>
        </div>
      </div>
    </div>
  );
}
