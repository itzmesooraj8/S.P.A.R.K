import { useState } from 'react';
import { Brain, Search, Plus, Loader2, Database, Trash2, BarChart2, BookOpen } from 'lucide-react';

const API = 'http://localhost:8000';

interface SearchResult {
  id: string;
  text: string;
  distance: number;
  similarity: number;
  metadata: Record<string, unknown>;
}

interface IndexStats {
  total_documents: number;
  collections: Record<string, number>;
}

const COLLECTIONS = [
  { id: 'spark_knowledge', label: 'KNOWLEDGE',     color: '#00f5ff' },
  { id: 'spark_conversations', label: 'MEMORY',    color: '#0066ff' },
  { id: 'spark_code', label: 'CODE',               color: '#00ff88' },
  { id: 'spark_notes', label: 'NOTES',             color: '#ff9f0a' },
];

export default function NeuralSearchModule() {
  const [query, setQuery] = useState('');
  const [collection, setCollection] = useState('spark_knowledge');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<IndexStats | null>(null);
  const [tab, setTab] = useState<'search' | 'index' | 'stats'>('search');
  const [indexText, setIndexText] = useState('');
  const [indexMeta, setIndexMeta] = useState('');
  const [indexed, setIndexed] = useState(false);
  const [topK, setTopK] = useState(5);

  const doSearch = async () => {
    if (!query.trim()) return;
    setLoading(true); setError(null); setResults([]);
    try {
      const res = await fetch(`${API}/api/neural-search/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: query.trim(), collection_name: collection, n_results: topK }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail ?? 'Search failed');
      }
      const data = await res.json();
      setResults(data.results ?? []);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const doIndex = async () => {
    if (!indexText.trim()) return;
    setLoading(true); setError(null); setIndexed(false);
    try {
      let metadata: Record<string, unknown> = {};
      if (indexMeta.trim()) {
        try { metadata = JSON.parse(indexMeta); } catch {}
      }
      const res = await fetch(`${API}/api/neural-search/index`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: indexText.trim(), collection_name: collection, metadata }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail ?? 'Index failed');
      }
      setIndexed(true);
      setIndexText(''); setIndexMeta('');
      loadStats();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const loadStats = async () => {
    try {
      const res = await fetch(`${API}/api/neural-search/stats`);
      const data = await res.json();
      setStats(data);
    } catch {}
  };

  const deleteDoc = async (docId: string) => {
    setLoading(true);
    try {
      await fetch(`${API}/api/neural-search/document/${docId}?collection_name=${collection}`, { method: 'DELETE' });
      setResults(prev => prev.filter(r => r.id !== docId));
    } catch {}
    setLoading(false);
  };

  const indexKB = async () => {
    setLoading(true); setError(null);
    try {
      const res = await fetch(`${API}/api/neural-search/index-knowledge-base`, { method: 'POST' });
      const data = await res.json();
      alert(`Indexed ${data.indexed_count ?? 0} documents from knowledge base`);
      loadStats();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'KB index failed');
    } finally {
      setLoading(false);
    }
  };

  const handleKey = (e: React.KeyboardEvent) => { if (e.key === 'Enter') doSearch(); };

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="px-4 pt-3 pb-2 border-b border-hud-cyan/20 shrink-0">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Brain size={14} className="text-hud-cyan" />
            <span className="font-orbitron text-xs tracking-widest neon-text">NEURAL SEARCH · CHROMADB</span>
            {loading && <Loader2 size={12} className="text-hud-cyan/50 animate-spin" />}
          </div>
          <button
            onClick={() => { setTab('stats'); loadStats(); }}
            className="flex items-center gap-1 font-orbitron text-[8px] px-2 py-0.5 rounded border border-hud-cyan/20 text-hud-cyan/50 hover:border-hud-cyan/40 hover:text-hud-cyan transition-all"
          >
            <BarChart2 size={9} /> STATS
          </button>
        </div>

        {/* Collection selector */}
        <div className="flex flex-wrap gap-1 mb-2">
          {COLLECTIONS.map(c => (
            <button
              key={c.id}
              onClick={() => setCollection(c.id)}
              className="font-orbitron text-[7px] px-2 py-0.5 rounded border transition-all"
              style={{
                borderColor: collection === c.id ? c.color : `${c.color}40`,
                color: collection === c.id ? c.color : `${c.color}60`,
                background: collection === c.id ? `${c.color}18` : 'transparent',
              }}
            >
              {c.label}
            </button>
          ))}
        </div>

        {/* Tabs */}
        <div className="flex gap-1">
          {(['search', 'index', 'stats'] as const).map(t => (
            <button
              key={t}
              onClick={() => { setTab(t); if (t === 'stats') loadStats(); }}
              className={`font-orbitron text-[8px] px-2 py-0.5 rounded border transition-all ${
                tab === t ? 'border-hud-cyan text-hud-cyan bg-hud-cyan/10' : 'border-hud-cyan/20 text-hud-cyan/40 hover:border-hud-cyan/40'
              }`}
            >
              {t.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto scrollbar-hud p-3 flex flex-col gap-3">
        {error && (
          <div className="p-2 rounded border border-hud-red/30 bg-hud-red/5">
            <span className="font-mono-tech text-[8px] text-hud-red/80">{error}</span>
          </div>
        )}

        {/* SEARCH tab */}
        {tab === 'search' && (
          <>
            <div className="flex gap-2">
              <input
                value={query}
                onChange={e => setQuery(e.target.value)}
                onKeyDown={handleKey}
                placeholder="SEMANTIC SEARCH QUERY..."
                className="flex-1 bg-transparent border border-hud-cyan/20 rounded px-2 py-1.5 font-mono-tech text-[9px] text-hud-cyan placeholder:text-hud-cyan/30 outline-none focus:border-hud-cyan/50"
              />
              <select
                value={topK}
                onChange={e => setTopK(Number(e.target.value))}
                className="bg-transparent border border-hud-cyan/20 rounded px-2 font-mono-tech text-[9px] text-hud-cyan outline-none"
              >
                <option value={3} className="bg-black">TOP 3</option>
                <option value={5} className="bg-black">TOP 5</option>
                <option value={10} className="bg-black">TOP 10</option>
              </select>
              <button
                onClick={doSearch}
                disabled={loading || !query.trim()}
                className="flex items-center gap-1 font-orbitron text-[8px] px-3 py-1 rounded border border-hud-cyan/40 text-hud-cyan hover:bg-hud-cyan/10 transition-all disabled:opacity-40"
              >
                <Search size={10} /> QUERY
              </button>
            </div>

            {results.length > 0 && (
              <div className="font-orbitron text-[8px] text-hud-cyan/50">
                {results.length} RESULTS IN <span className="text-hud-cyan">{collection.replace('spark_', '').toUpperCase()}</span>
              </div>
            )}

            {results.map((r, i) => (
              <div key={r.id} className="hud-panel rounded p-3 flex flex-col gap-1.5">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="font-orbitron text-[9px] text-hud-cyan/40">#{i + 1}</span>
                    <div
                      className="h-1.5 rounded-full"
                      style={{ width: `${Math.round(r.similarity * 100)}px`, maxWidth: '60px', background: r.similarity > 0.8 ? '#30d158' : r.similarity > 0.5 ? '#ff9f0a' : '#636366' }}
                    />
                    <span className="font-mono-tech text-[8px]" style={{ color: r.similarity > 0.8 ? '#30d158' : r.similarity > 0.5 ? '#ff9f0a' : '#636366' }}>
                      {Math.round(r.similarity * 100)}% match
                    </span>
                  </div>
                  <button onClick={() => deleteDoc(r.id)} className="text-hud-red/30 hover:text-hud-red transition-colors">
                    <Trash2 size={9} />
                  </button>
                </div>
                <div className="font-mono-tech text-[8px] text-hud-cyan/70 leading-relaxed">
                  {r.text.slice(0, 400)}{r.text.length > 400 ? '…' : ''}
                </div>
                {Object.keys(r.metadata).length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {Object.entries(r.metadata).slice(0, 4).map(([k, v]) => (
                      <span key={k} className="font-mono-tech text-[6px] px-1 rounded border border-hud-cyan/20 text-hud-cyan/40">
                        {k}: {String(v).slice(0, 20)}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}

            {!loading && results.length === 0 && query && (
              <div className="flex items-center justify-center h-24 text-hud-cyan/30">
                <span className="font-orbitron text-[9px]">NO MATCHES FOUND</span>
              </div>
            )}

            {!loading && !query && (
              <div className="flex flex-col items-center justify-center h-32 text-hud-cyan/20">
                <Brain size={28} className="mb-2 opacity-40" />
                <span className="font-orbitron text-[9px]">VECTOR MEMORY SEARCH</span>
                <span className="font-mono-tech text-[8px] mt-1 text-hud-cyan/15">POWERED BY CHROMADB</span>
              </div>
            )}
          </>
        )}

        {/* INDEX tab */}
        {tab === 'index' && (
          <div className="flex flex-col gap-3">
            <textarea
              value={indexText}
              onChange={e => setIndexText(e.target.value)}
              placeholder="ENTER TEXT TO INDEX INTO VECTOR MEMORY..."
              rows={6}
              className="w-full bg-transparent border border-hud-cyan/20 rounded px-2 py-1.5 font-mono-tech text-[9px] text-hud-cyan placeholder:text-hud-cyan/30 outline-none focus:border-hud-cyan/50 resize-none"
            />
            <input
              value={indexMeta}
              onChange={e => setIndexMeta(e.target.value)}
              placeholder='METADATA JSON (optional) e.g. {"source": "manual", "tag": "research"}'
              className="w-full bg-transparent border border-hud-cyan/20 rounded px-2 py-1.5 font-mono-tech text-[8px] text-hud-cyan placeholder:text-hud-cyan/30 outline-none focus:border-hud-cyan/50"
            />
            <div className="flex gap-2">
              <button
                onClick={doIndex}
                disabled={loading || !indexText.trim()}
                className="flex-1 flex items-center justify-center gap-1 font-orbitron text-[8px] px-2 py-1.5 rounded border border-hud-cyan/40 text-hud-cyan hover:bg-hud-cyan/10 transition-all disabled:opacity-40"
              >
                <Plus size={10} /> INDEX DOCUMENT
              </button>
              <button
                onClick={indexKB}
                disabled={loading}
                className="flex items-center justify-center gap-1 font-orbitron text-[8px] px-3 py-1.5 rounded border border-hud-purple/40 text-hud-purple/70 hover:border-hud-purple hover:bg-hud-purple/10 transition-all disabled:opacity-40"
              >
                <BookOpen size={10} /> INDEX KB
              </button>
            </div>
            {indexed && (
              <div className="p-2 rounded border border-hud-green/30 bg-hud-green/5">
                <span className="font-orbitron text-[8px] text-hud-green">✓ DOCUMENT INDEXED SUCCESSFULLY</span>
              </div>
            )}
          </div>
        )}

        {/* STATS tab */}
        {tab === 'stats' && (
          <div className="flex flex-col gap-3">
            {stats ? (
              <>
                <div className="hud-panel rounded p-3 text-center">
                  <div className="font-orbitron text-2xl text-hud-cyan font-bold">{stats.total_documents}</div>
                  <div className="font-orbitron text-[8px] text-hud-cyan/50 mt-1">TOTAL VECTORS</div>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  {COLLECTIONS.map(c => (
                    <div key={c.id} className="hud-panel rounded p-3" style={{ borderLeft: `3px solid ${c.color}` }}>
                      <div className="font-orbitron text-lg font-bold" style={{ color: c.color }}>
                        {stats.collections[c.id] ?? 0}
                      </div>
                      <div className="font-orbitron text-[7px] text-hud-cyan/40 mt-0.5">{c.label}</div>
                    </div>
                  ))}
                </div>
                <div className="hud-panel rounded p-3">
                  <div className="font-orbitron text-[8px] text-hud-cyan/50 mb-2">COLLECTION DISTRIBUTION</div>
                  {COLLECTIONS.map(c => {
                    const count = stats.collections[c.id] ?? 0;
                    const pct = stats.total_documents > 0 ? (count / stats.total_documents) * 100 : 0;
                    return (
                      <div key={c.id} className="flex items-center gap-2 mb-1.5">
                        <span className="font-orbitron text-[7px] w-20 shrink-0" style={{ color: c.color }}>{c.label}</span>
                        <div className="flex-1 h-1.5 bg-hud-cyan/10 rounded-full overflow-hidden">
                          <div className="h-full rounded-full transition-all duration-500" style={{ width: `${pct}%`, background: c.color }} />
                        </div>
                        <span className="font-mono-tech text-[7px] text-hud-cyan/40 w-8 text-right">{count}</span>
                      </div>
                    );
                  })}
                </div>
                <div className="flex items-center gap-2">
                  <Database size={10} className="text-hud-cyan/40" />
                  <span className="font-mono-tech text-[8px] text-hud-cyan/40">ChromaDB · PersistentClient · spark_memory_db/</span>
                </div>
              </>
            ) : (
              <div className="flex items-center justify-center h-32">
                <button
                  onClick={loadStats}
                  className="font-orbitron text-[9px] px-3 py-1.5 rounded border border-hud-cyan/30 text-hud-cyan/60 hover:border-hud-cyan/60"
                >
                  LOAD STATS
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
