import { useState } from 'react';
import { Globe, Search, Camera, ArrowRight, X, Loader2, History, ExternalLink, AlertTriangle } from 'lucide-react';

const API = 'http://localhost:8000';

interface BrowseResult {
  url: string;
  title: string;
  status: number;
  content?: string;
  screenshot?: string;
}

interface SearchResult {
  query: string;
  results: Array<{ url: string; title: string; snippet: string }>;
}

interface HistoryEntry {
  url: string;
  title: string;
  timestamp: string;
  status: number;
}

export default function BrowserModule() {
  const [url, setUrl] = useState('');
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<BrowseResult | null>(null);
  const [searchResults, setSearchResults] = useState<SearchResult | null>(null);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [screenshot, setScreenshot] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<'browse' | 'search' | 'history'>('browse');
  const [extractDepth, setExtractDepth] = useState(1);

  const navigate = async () => {
    if (!url.trim()) return;
    setLoading(true); setError(null); setResult(null); setScreenshot(null);
    try {
      const res = await fetch(`${API}/api/browser/navigate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url.trim() }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail ?? 'Navigation failed');
      }
      const data = await res.json();
      setResult(data);
      // auto-load history
      loadHistory();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const takeScreenshot = async () => {
    setLoading(true); setError(null);
    try {
      const res = await fetch(`${API}/api/browser/screenshot`, { method: 'POST' });
      const data = await res.json();
      if (data.screenshot) setScreenshot(data.screenshot);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Screenshot failed');
    } finally {
      setLoading(false);
    }
  };

  const doSearch = async () => {
    if (!query.trim()) return;
    setLoading(true); setError(null); setSearchResults(null);
    try {
      const res = await fetch(`${API}/api/browser/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: query.trim() }),
      });
      const data = await res.json();
      setSearchResults(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Search failed');
    } finally {
      setLoading(false);
    }
  };

  const extractContent = async () => {
    setLoading(true); setError(null);
    try {
      const res = await fetch(`${API}/api/browser/extract`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ depth: extractDepth }),
      });
      const data = await res.json();
      setResult(prev => prev ? { ...prev, content: data.content } : null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Extract failed');
    } finally {
      setLoading(false);
    }
  };

  const loadHistory = async () => {
    try {
      const res = await fetch(`${API}/api/browser/history`);
      const data = await res.json();
      setHistory(data.history ?? []);
    } catch {}
  };

  const closeBrowser = async () => {
    await fetch(`${API}/api/browser/close`, { method: 'POST' });
    setResult(null); setScreenshot(null);
  };

  const handleKeyNav = (e: React.KeyboardEvent) => { if (e.key === 'Enter') navigate(); };
  const handleKeySearch = (e: React.KeyboardEvent) => { if (e.key === 'Enter') doSearch(); };

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="px-4 pt-3 pb-2 border-b border-hud-cyan/20 shrink-0">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Globe size={14} className="text-hud-cyan" />
            <span className="font-orbitron text-xs tracking-widest neon-text">BROWSER AGENT</span>
            {loading && <Loader2 size={12} className="text-hud-cyan/50 animate-spin" />}
          </div>
          <div className="flex items-center gap-2">
            {result && (
              <button
                onClick={closeBrowser}
                className="flex items-center gap-1 font-orbitron text-[8px] px-2 py-0.5 rounded border border-hud-red/30 text-hud-red/60 hover:border-hud-red/60 transition-all"
              >
                <X size={9} /> CLOSE
              </button>
            )}
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mb-2">
          {(['browse', 'search', 'history'] as const).map(t => (
            <button
              key={t}
              onClick={() => { setTab(t); if (t === 'history') loadHistory(); }}
              className={`font-orbitron text-[8px] px-2 py-0.5 rounded border transition-all ${
                tab === t ? 'border-hud-cyan text-hud-cyan bg-hud-cyan/10' : 'border-hud-cyan/20 text-hud-cyan/40 hover:border-hud-cyan/40'
              }`}
            >
              {t.toUpperCase()}
            </button>
          ))}
        </div>

        {/* Browse bar */}
        {tab === 'browse' && (
          <div className="flex gap-2">
            <input
              value={url}
              onChange={e => setUrl(e.target.value)}
              onKeyDown={handleKeyNav}
              placeholder="ENTER URL (https://...)"
              className="flex-1 bg-transparent border border-hud-cyan/20 rounded px-2 py-1 font-mono-tech text-[9px] text-hud-cyan placeholder:text-hud-cyan/30 outline-none focus:border-hud-cyan/50"
            />
            <button
              onClick={navigate}
              disabled={loading || !url.trim()}
              className="flex items-center gap-1 font-orbitron text-[8px] px-3 py-1 rounded border border-hud-cyan/40 text-hud-cyan hover:bg-hud-cyan/10 transition-all disabled:opacity-40"
            >
              <ArrowRight size={10} /> GO
            </button>
          </div>
        )}

        {/* Search bar */}
        {tab === 'search' && (
          <div className="flex gap-2">
            <input
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={handleKeySearch}
              placeholder="WEB SEARCH QUERY..."
              className="flex-1 bg-transparent border border-hud-cyan/20 rounded px-2 py-1 font-mono-tech text-[9px] text-hud-cyan placeholder:text-hud-cyan/30 outline-none focus:border-hud-cyan/50"
            />
            <button
              onClick={doSearch}
              disabled={loading || !query.trim()}
              className="flex items-center gap-1 font-orbitron text-[8px] px-3 py-1 rounded border border-hud-cyan/40 text-hud-cyan hover:bg-hud-cyan/10 transition-all disabled:opacity-40"
            >
              <Search size={10} /> SEARCH
            </button>
          </div>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto scrollbar-hud p-3 flex flex-col gap-3">
        {error && (
          <div className="flex items-start gap-2 p-3 rounded border border-hud-red/30 bg-hud-red/5">
            <AlertTriangle size={12} className="text-hud-red mt-0.5 shrink-0" />
            <div>
              <div className="font-orbitron text-[9px] text-hud-red mb-1">BROWSER ERROR</div>
              <div className="font-mono-tech text-[8px] text-hud-red/70">{error}</div>
              {error.toLowerCase().includes('playwright') && (
                <div className="font-mono-tech text-[8px] text-hud-amber/60 mt-1">
                  Run: <code className="text-hud-amber">playwright install chromium</code>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Browse result */}
        {tab === 'browse' && result && (
          <div className="flex flex-col gap-3">
            <div className="hud-panel rounded p-3">
              <div className="flex items-center justify-between mb-2">
                <div>
                  <div className="font-orbitron text-[10px] text-hud-cyan">{result.title || 'Untitled'}</div>
                  <div className="font-mono-tech text-[8px] text-hud-cyan/40 mt-0.5">{result.url}</div>
                </div>
                <span className={`font-orbitron text-[8px] px-1.5 py-0.5 rounded border ${result.status === 200 ? 'border-hud-green/40 text-hud-green' : 'border-hud-amber/40 text-hud-amber'}`}>
                  {result.status}
                </span>
              </div>

              <div className="flex gap-2">
                <button onClick={takeScreenshot} disabled={loading} className="flex items-center gap-1 font-orbitron text-[7px] px-2 py-1 rounded border border-hud-cyan/30 text-hud-cyan/60 hover:border-hud-cyan/60 transition-all">
                  <Camera size={9} /> SCREENSHOT
                </button>
                <button onClick={extractContent} disabled={loading} className="flex items-center gap-1 font-orbitron text-[7px] px-2 py-1 rounded border border-hud-cyan/30 text-hud-cyan/60 hover:border-hud-cyan/60 transition-all">
                  <ExternalLink size={9} /> EXTRACT
                </button>
                <select
                  value={extractDepth}
                  onChange={e => setExtractDepth(Number(e.target.value))}
                  className="bg-transparent border border-hud-cyan/20 rounded px-1 py-0 font-mono-tech text-[8px] text-hud-cyan outline-none"
                >
                  <option value={1} className="bg-black">DEPTH 1</option>
                  <option value={2} className="bg-black">DEPTH 2</option>
                  <option value={3} className="bg-black">DEPTH 3</option>
                </select>
              </div>
            </div>

            {screenshot && (
              <div className="hud-panel rounded overflow-hidden">
                <div className="font-orbitron text-[8px] text-hud-cyan/50 px-2 py-1 border-b border-hud-cyan/10">SCREENSHOT</div>
                <img src={`data:image/png;base64,${screenshot}`} alt="Browser screenshot" className="w-full" />
              </div>
            )}

            {result.content && (
              <div className="hud-panel rounded p-3">
                <div className="font-orbitron text-[8px] text-hud-cyan/50 mb-2">EXTRACTED CONTENT</div>
                <div className="font-mono-tech text-[8px] text-hud-cyan/70 leading-relaxed max-h-64 overflow-y-auto scrollbar-hud whitespace-pre-wrap">
                  {result.content.slice(0, 3000)}{result.content.length > 3000 ? '\n...[truncated]' : ''}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Search results */}
        {tab === 'search' && searchResults && (
          <div className="flex flex-col gap-2">
            <div className="font-orbitron text-[8px] text-hud-cyan/50 mb-1">
              RESULTS FOR: "{searchResults.query}"
            </div>
            {searchResults.results.map((r, i) => (
              <div key={i} className="hud-panel rounded p-3">
                <div className="font-orbitron text-[10px] text-hud-cyan mb-1">{r.title}</div>
                <div className="font-mono-tech text-[8px] text-hud-purple/70 mb-1.5 truncate">{r.url}</div>
                <div className="font-mono-tech text-[8px] text-hud-cyan/50 leading-relaxed">{r.snippet}</div>
                <button
                  onClick={() => { setUrl(r.url); setTab('browse'); setTimeout(navigate, 100); }}
                  className="mt-1.5 flex items-center gap-1 font-orbitron text-[7px] text-hud-cyan/50 hover:text-hud-cyan transition-colors"
                >
                  <ArrowRight size={8} /> OPEN
                </button>
              </div>
            ))}
          </div>
        )}

        {/* History */}
        {tab === 'history' && (
          <div className="flex flex-col gap-2">
            {history.length === 0 ? (
              <div className="flex items-center justify-center h-32 text-hud-cyan/30">
                <div className="text-center">
                  <History size={24} className="mx-auto mb-2 opacity-40" />
                  <span className="font-orbitron text-[9px]">NO BROWSING HISTORY</span>
                </div>
              </div>
            ) : (
              history.map((h, i) => (
                <div
                  key={i}
                  className="hud-panel rounded p-2 flex items-center justify-between cursor-pointer hover:border-hud-cyan/40 transition-all"
                  onClick={() => { setUrl(h.url); setTab('browse'); }}
                >
                  <div className="min-w-0">
                    <div className="font-orbitron text-[9px] text-hud-cyan truncate">{h.title || h.url}</div>
                    <div className="font-mono-tech text-[7px] text-hud-cyan/40 truncate">{h.url}</div>
                  </div>
                  <div className="text-right shrink-0 ml-3">
                    <span className={`font-orbitron text-[7px] ${h.status === 200 ? 'text-hud-green/60' : 'text-hud-amber/60'}`}>{h.status}</span>
                    <div className="font-mono-tech text-[7px] text-hud-cyan/30">{new Date(h.timestamp).toLocaleDateString()}</div>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {!loading && !result && !error && tab === 'browse' && (
          <div className="flex flex-col items-center justify-center h-32 text-hud-cyan/20">
            <Globe size={28} className="mb-2 opacity-40" />
            <span className="font-orbitron text-[9px]">ENTER URL TO BEGIN BROWSING</span>
          </div>
        )}
      </div>
    </div>
  );
}
