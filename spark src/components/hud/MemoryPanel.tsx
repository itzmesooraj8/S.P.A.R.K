import { useEffect, useMemo, useState } from 'react';
import { Brain, RefreshCw, Search, Trash2 } from 'lucide-react';

const API = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000';

type MemoryItem = {
  id: string;
  text: string;
  metadata?: Record<string, unknown>;
  saved_at?: number;
  similarity?: number;
};

export default function MemoryPanel() {
  const [items, setItems] = useState<MemoryItem[]>([]);
  const [query, setQuery] = useState('');
  const [sessionId, setSessionId] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const sessionQuery = useMemo(() => {
    const value = sessionId.trim();
    return value ? `&session_id=${encodeURIComponent(value)}` : '';
  }, [sessionId]);

  const loadRecent = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${API}/api/memory/chroma/recent?limit=30${sessionQuery}`);
      if (!res.ok) throw new Error('Failed to load memory');
      const data = await res.json();
      setItems(Array.isArray(data.items) ? data.items : []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load memory');
    } finally {
      setLoading(false);
    }
  };

  const runSearch = async () => {
    const q = query.trim();
    if (!q) {
      loadRecent();
      return;
    }

    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${API}/api/memory/chroma/search?q=${encodeURIComponent(q)}&limit=25${sessionQuery}`);
      if (!res.ok) throw new Error('Search failed');
      const data = await res.json();
      setItems(Array.isArray(data.items) ? data.items : []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed');
    } finally {
      setLoading(false);
    }
  };

  const deleteItem = async (id: string) => {
    try {
      const res = await fetch(`${API}/api/memory/chroma/${encodeURIComponent(id)}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Delete failed');
      setItems((prev) => prev.filter((item) => item.id !== id));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Delete failed');
    }
  };

  useEffect(() => {
    loadRecent();
    const timer = window.setInterval(loadRecent, 15000);
    return () => window.clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionQuery]);

  return (
    <div className="h-full flex flex-col gap-2 overflow-y-auto scrollbar-hud p-2 animate-boot-left" style={{ animationDelay: '0.25s' }}>
      <div className="flex items-center justify-between pb-1 border-b border-hud-cyan/20">
        <span className="font-orbitron text-[9px] tracking-widest neon-text">MEMORY VIEWER</span>
        <button
          onClick={loadRecent}
          className="p-1 rounded border border-hud-cyan/25 text-hud-cyan/60 hover:text-hud-cyan"
          title="Refresh"
        >
          <RefreshCw size={10} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>

      <input
        value={sessionId}
        onChange={(e) => setSessionId(e.target.value)}
        placeholder="SESSION FILTER (optional)"
        className="bg-transparent border border-hud-cyan/20 rounded px-2 py-1 font-mono-tech text-[8px] text-hud-cyan placeholder:text-hud-cyan/30 outline-none focus:border-hud-cyan/50"
      />

      <div className="flex gap-1.5">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && runSearch()}
          placeholder="SEARCH MEMORY..."
          className="flex-1 bg-transparent border border-hud-cyan/20 rounded px-2 py-1 font-mono-tech text-[8px] text-hud-cyan placeholder:text-hud-cyan/30 outline-none focus:border-hud-cyan/50"
        />
        <button
          onClick={runSearch}
          className="px-2 py-1 rounded border border-hud-cyan/30 text-hud-cyan/70 hover:border-hud-cyan/70"
          title="Search"
        >
          <Search size={10} />
        </button>
      </div>

      {error && (
        <div className="p-1.5 rounded border border-hud-red/40 bg-hud-red/10 font-mono-tech text-[8px] text-hud-red/80">
          {error}
        </div>
      )}

      <div className="flex-1 overflow-y-auto scrollbar-hud flex flex-col gap-1.5">
        {!loading && items.length === 0 && (
          <div className="h-full min-h-20 flex flex-col items-center justify-center text-hud-cyan/30">
            <Brain size={20} className="mb-1" />
            <span className="font-orbitron text-[8px]">NO MEMORY FOUND</span>
          </div>
        )}

        {items.map((item) => {
          const role = String(item.metadata?.role || item.metadata?.source || 'memory');
          const similarity = typeof item.similarity === 'number' ? Math.round(item.similarity * 100) : null;
          return (
            <div key={item.id} className="p-2 rounded border border-hud-cyan/15 bg-black/30">
              <div className="flex items-center gap-1 mb-1">
                <span className="font-orbitron text-[7px] text-hud-cyan/60 uppercase">{role}</span>
                {similarity !== null && (
                  <span className="font-mono-tech text-[7px] text-hud-green/80">{similarity}%</span>
                )}
                <button
                  onClick={() => deleteItem(item.id)}
                  className="ml-auto text-hud-red/40 hover:text-hud-red transition-colors"
                  title="Delete memory item"
                >
                  <Trash2 size={9} />
                </button>
              </div>
              <div className="font-mono-tech text-[8px] text-hud-cyan/80 leading-relaxed">
                {item.text?.slice(0, 280)}
                {(item.text?.length || 0) > 280 ? '…' : ''}
              </div>
              <div className="font-mono-tech text-[7px] text-hud-cyan/35 mt-1">{item.id}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
