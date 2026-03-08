import { useState } from 'react';
import {
  Brain, Search, Plus, Loader2, Database, Trash2, BarChart2, BookOpen,
  Clock, Bell, CheckCircle, AlertTriangle, AlertOctagon, History, Calendar,
} from 'lucide-react';
import { useContextStore } from '@/store/useContextStore';
import { useScheduler } from '@/hooks/useScheduler';
import type { CreateReminderPayload, Reminder } from '@/hooks/useScheduler';

const API = 'http://localhost:8000';
const ACCENT = '#00ff88';

// ── Neural Search types ────────────────────────────────────────────────────
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
  { id: 'spark_knowledge',     label: 'KNOWLEDGE', color: '#00f5ff' },
  { id: 'spark_conversations', label: 'MEMORY',    color: '#0066ff' },
  { id: 'spark_code',          label: 'CODE',      color: '#00ff88' },
  { id: 'spark_notes',         label: 'NOTES',     color: '#ff9f0a' },
];

// ── Scheduler types ────────────────────────────────────────────────────────
const SEVERITY_CFG = {
  info:     { color: '#00f5ff', icon: Bell,          label: 'INFO'     },
  warning:  { color: '#ff9f0a', icon: AlertTriangle, label: 'WARNING'  },
  critical: { color: '#ff453a', icon: AlertOctagon,  label: 'CRITICAL' },
};

// ═══════════════════════════════════════════════════════════════════════════
// ReminderCard
// ═══════════════════════════════════════════════════════════════════════════
function ReminderCard({ reminder, onDelete, onToggle }: {
  reminder: Reminder;
  onDelete: (id: string) => void;
  onToggle: (id: string, enabled: boolean) => void;
}) {
  const sev = SEVERITY_CFG[reminder.severity];
  const SevIcon = sev.icon;
  const fmt = (iso: string | null) => iso ? new Date(iso).toLocaleString() : '—';
  const triggerLabel = reminder.fire_at
    ? `📅 ${fmt(reminder.fire_at)}`
    : reminder.cron
    ? `⚙️ CRON: ${reminder.cron}`
    : reminder.interval_seconds
    ? `🔁 Every ${reminder.interval_seconds}s`
    : '?';

  return (
    <div
      className={`hud-panel rounded p-3 flex flex-col gap-2 transition-all ${!reminder.enabled ? 'opacity-50' : ''}`}
      style={{ borderLeft: `3px solid ${sev.color}` }}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <SevIcon size={12} style={{ color: sev.color, flexShrink: 0 }} />
          <div className="min-w-0">
            <div className="font-orbitron text-[10px] text-hud-cyan truncate">{reminder.title}</div>
            <div className="font-mono-tech text-[8px] text-hud-cyan/40 mt-0.5">{triggerLabel}</div>
          </div>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          <button
            onClick={() => onToggle(reminder.id, !reminder.enabled)}
            className={`font-orbitron text-[7px] px-1.5 py-0.5 rounded border transition-all ${
              reminder.enabled
                ? 'border-hud-green/40 text-hud-green/70 hover:border-hud-green'
                : 'border-hud-cyan/20 text-hud-cyan/30 hover:border-hud-cyan/50'
            }`}
          >
            {reminder.enabled ? '● ON' : '○ OFF'}
          </button>
          <button
            onClick={() => onDelete(reminder.id)}
            className="text-hud-red/40 hover:text-hud-red transition-colors p-0.5"
          >
            <Trash2 size={10} />
          </button>
        </div>
      </div>
      {reminder.body && (
        <div className="font-mono-tech text-[8px] text-hud-cyan/50 leading-relaxed">{reminder.body}</div>
      )}
      <div className="flex items-center gap-3">
        <span className="font-mono-tech text-[7px] text-hud-cyan/30">
          Fired: <span className="text-hud-cyan/50">{reminder.fired_count}×</span>
        </span>
        {reminder.last_fired && (
          <span className="font-mono-tech text-[7px] text-hud-cyan/30">
            Last: <span className="text-hud-cyan/50">{fmt(reminder.last_fired)}</span>
          </span>
        )}
        {reminder.repeat && (
          <span className="font-orbitron text-[6px] text-hud-amber/60 border border-hud-amber/30 px-1 rounded">REPEAT</span>
        )}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// CreateReminderForm
// ═══════════════════════════════════════════════════════════════════════════
function CreateReminderForm({ onSubmit, isCreating }: {
  onSubmit: (p: CreateReminderPayload) => void;
  isCreating: boolean;
}) {
  const [title, setTitle]           = useState('');
  const [body, setBody]             = useState('');
  const [fireAt, setFireAt]         = useState('');
  const [cron, setCron]             = useState('');
  const [intervalSec, setInterval]  = useState('');
  const [severity, setSeverity]     = useState<'info' | 'warning' | 'critical'>('info');
  const [repeat, setRepeat]         = useState(false);
  const [open, setOpen]             = useState(false);

  const submit = () => {
    if (!title.trim()) return;
    const payload: CreateReminderPayload = { title: title.trim(), body: body.trim(), severity, repeat };
    if (fireAt) payload.fire_at = new Date(fireAt).toISOString();
    if (cron) payload.cron = cron;
    if (intervalSec) payload.interval_seconds = parseInt(intervalSec, 10);
    onSubmit(payload);
    setTitle(''); setBody(''); setFireAt(''); setCron(''); setInterval('');
    setOpen(false);
  };

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="w-full flex items-center justify-center gap-2 py-2.5 rounded border border-dashed text-[9px] font-orbitron transition-all hover:opacity-80"
        style={{ borderColor: `${ACCENT}40`, color: `${ACCENT}80` }}
      >
        <Plus size={12} /> ADD REMINDER
      </button>
    );
  }

  return (
    <div className="hud-panel rounded p-3 flex flex-col gap-2">
      <div className="font-orbitron text-[9px] text-hud-cyan/70 mb-1 flex items-center gap-1">
        <Plus size={10} /> NEW REMINDER
      </div>
      <input
        value={title} onChange={e => setTitle(e.target.value)} placeholder="TITLE *"
        className="bg-transparent border border-hud-cyan/20 rounded px-2 py-1 font-mono-tech text-[9px] text-hud-cyan placeholder:text-hud-cyan/30 outline-none focus:border-hud-cyan/50"
      />
      <input
        value={body} onChange={e => setBody(e.target.value)} placeholder="MESSAGE (optional)"
        className="bg-transparent border border-hud-cyan/20 rounded px-2 py-1 font-mono-tech text-[9px] text-hud-cyan placeholder:text-hud-cyan/30 outline-none focus:border-hud-cyan/50"
      />
      <div className="grid grid-cols-3 gap-2">
        <div className="flex flex-col gap-1">
          <label className="font-orbitron text-[7px] text-hud-cyan/40">FIRE AT</label>
          <input type="datetime-local" value={fireAt} onChange={e => setFireAt(e.target.value)}
            className="bg-transparent border border-hud-cyan/20 rounded px-2 py-1 font-mono-tech text-[8px] text-hud-cyan outline-none focus:border-hud-cyan/50 [color-scheme:dark]" />
        </div>
        <div className="flex flex-col gap-1">
          <label className="font-orbitron text-[7px] text-hud-cyan/40">CRON</label>
          <input value={cron} onChange={e => setCron(e.target.value)} placeholder="0 9 * * *"
            className="bg-transparent border border-hud-cyan/20 rounded px-2 py-1 font-mono-tech text-[8px] text-hud-cyan placeholder:text-hud-cyan/30 outline-none focus:border-hud-cyan/50" />
        </div>
        <div className="flex flex-col gap-1">
          <label className="font-orbitron text-[7px] text-hud-cyan/40">EVERY (sec)</label>
          <input type="number" value={intervalSec} onChange={e => setInterval(e.target.value)} placeholder="3600"
            className="bg-transparent border border-hud-cyan/20 rounded px-2 py-1 font-mono-tech text-[8px] text-hud-cyan placeholder:text-hud-cyan/30 outline-none focus:border-hud-cyan/50" />
        </div>
      </div>
      <div className="flex items-center gap-3">
        <div className="flex gap-1">
          {(['info', 'warning', 'critical'] as const).map(s => {
            const cfg = SEVERITY_CFG[s];
            return (
              <button key={s} onClick={() => setSeverity(s)}
                className="font-orbitron text-[7px] px-1.5 py-0.5 rounded border transition-all"
                style={{
                  borderColor: severity === s ? cfg.color : `${cfg.color}40`,
                  color: severity === s ? cfg.color : `${cfg.color}60`,
                  background: severity === s ? `${cfg.color}18` : 'transparent',
                }}
              >{cfg.label}</button>
            );
          })}
        </div>
        <label className="flex items-center gap-1 cursor-pointer">
          <input type="checkbox" checked={repeat} onChange={e => setRepeat(e.target.checked)} className="accent-hud-cyan w-3 h-3" />
          <span className="font-orbitron text-[8px] text-hud-cyan/50">REPEAT</span>
        </label>
      </div>
      <div className="flex gap-2 mt-1">
        <button onClick={submit} disabled={!title.trim() || isCreating}
          className="flex-1 flex items-center justify-center gap-1 font-orbitron text-[8px] px-2 py-1.5 rounded border border-hud-cyan/40 text-hud-cyan hover:bg-hud-cyan/10 transition-all disabled:opacity-40"
        >
          {isCreating ? <Loader2 size={10} className="animate-spin" /> : <CheckCircle size={10} />} CREATE
        </button>
        <button onClick={() => setOpen(false)}
          className="font-orbitron text-[8px] px-3 py-1.5 rounded border border-hud-red/30 text-hud-red/60 hover:border-hud-red/60 transition-all"
        >
          CANCEL
        </button>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// SEARCH TAB
// ═══════════════════════════════════════════════════════════════════════════
function SearchTab() {
  const { setSelectedItem } = useContextStore();
  const [query, setQuery]         = useState('');
  const [collection, setCollect]  = useState('spark_knowledge');
  const [results, setResults]     = useState<SearchResult[]>([]);
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState<string | null>(null);
  const [stats, setStats]         = useState<IndexStats | null>(null);
  const [subTab, setSubTab]       = useState<'search' | 'index' | 'stats'>('search');
  const [indexText, setIndexText] = useState('');
  const [indexMeta, setIndexMeta] = useState('');
  const [indexed, setIndexed]     = useState(false);
  const [topK, setTopK]           = useState(5);

  const doSearch = async () => {
    if (!query.trim()) return;
    setLoading(true); setError(null); setResults([]);
    try {
      const res = await fetch(`${API}/api/neural-search/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: query.trim(), collection_name: collection, n_results: topK }),
      });
      if (!res.ok) { const e = await res.json(); throw new Error(e.detail ?? 'Search failed'); }
      const data = await res.json();
      setResults(data.results ?? []);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Unknown error');
    } finally { setLoading(false); }
  };

  const doIndex = async () => {
    if (!indexText.trim()) return;
    setLoading(true); setError(null); setIndexed(false);
    try {
      let metadata: Record<string, unknown> = {};
      if (indexMeta.trim()) { try { metadata = JSON.parse(indexMeta); } catch { /* invalid JSON — ignore */ } }
      const res = await fetch(`${API}/api/neural-search/index`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: indexText.trim(), collection_name: collection, metadata }),
      });
      if (!res.ok) { const e = await res.json(); throw new Error(e.detail ?? 'Index failed'); }
      setIndexed(true); setIndexText(''); setIndexMeta('');
      loadStats();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Unknown error');
    } finally { setLoading(false); }
  };

  const loadStats = async () => {
    try {
      const res = await fetch(`${API}/api/neural-search/stats`);
      setStats(await res.json());
    } catch { /* network error */ }
  };

  const deleteDoc = async (docId: string) => {
    setLoading(true);
    try {
      await fetch(`${API}/api/neural-search/document/${docId}?collection_name=${collection}`, { method: 'DELETE' });
      setResults(prev => prev.filter(r => r.id !== docId));
    } catch { /* network error — ignore */ } finally { setLoading(false); }
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
    } finally { setLoading(false); }
  };

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Collection selector */}
      <div className="px-3 pt-2 pb-1 shrink-0">
        <div className="flex flex-wrap gap-1 mb-2">
          {COLLECTIONS.map(c => (
            <button key={c.id} onClick={() => setCollect(c.id)}
              className="font-orbitron text-[7px] px-2 py-0.5 rounded border transition-all"
              style={{
                borderColor: collection === c.id ? c.color : `${c.color}40`,
                color: collection === c.id ? c.color : `${c.color}60`,
                background: collection === c.id ? `${c.color}18` : 'transparent',
              }}
            >{c.label}</button>
          ))}
        </div>
        <div className="flex gap-1">
          {(['search', 'index', 'stats'] as const).map(t => (
            <button key={t} onClick={() => { setSubTab(t); if (t === 'stats') loadStats(); }}
              className="font-orbitron text-[8px] px-2 py-0.5 rounded border transition-all"
              style={{
                borderColor: subTab === t ? ACCENT : `${ACCENT}30`,
                color: subTab === t ? ACCENT : `${ACCENT}50`,
                background: subTab === t ? `${ACCENT}15` : 'transparent',
              }}
            >{t.toUpperCase()}</button>
          ))}
          {loading && <Loader2 size={12} className="ml-auto animate-spin" style={{ color: `${ACCENT}80` }} />}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto scrollbar-hud p-3 flex flex-col gap-3">
        {error && (
          <div className="p-2 rounded border border-hud-red/30 bg-hud-red/5">
            <span className="font-mono-tech text-[8px] text-hud-red/80">{error}</span>
          </div>
        )}

        {subTab === 'search' && (
          <>
            <div className="flex gap-2">
              <input value={query} onChange={e => setQuery(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && doSearch()}
                placeholder="SEMANTIC SEARCH QUERY..."
                className="flex-1 bg-transparent border border-hud-cyan/20 rounded px-2 py-1.5 font-mono-tech text-[9px] text-hud-cyan placeholder:text-hud-cyan/30 outline-none focus:border-hud-cyan/50"
              />
              <select value={topK} onChange={e => setTopK(Number(e.target.value))}
                className="bg-transparent border border-hud-cyan/20 rounded px-2 font-mono-tech text-[9px] text-hud-cyan outline-none"
              >
                <option value={3} className="bg-black">TOP 3</option>
                <option value={5} className="bg-black">TOP 5</option>
                <option value={10} className="bg-black">TOP 10</option>
              </select>
              <button onClick={doSearch} disabled={loading || !query.trim()}
                className="flex items-center gap-1 font-orbitron text-[8px] px-3 py-1 rounded border transition-all disabled:opacity-40"
                style={{ borderColor: `${ACCENT}60`, color: ACCENT }}
              >
                <Search size={10} /> QUERY
              </button>
            </div>
            {results.map((r, i) => (
              <div key={r.id}
                className="hud-panel rounded p-3 flex flex-col gap-1.5 cursor-pointer hover:border-hud-cyan/40 transition-colors"
                onClick={() => setSelectedItem({ module: 'neural_search', type: 'search_result', label: r.text.slice(0, 60) + (r.text.length > 60 ? '…' : ''), data: { id: r.id, text: r.text, similarity: r.similarity, collection, metadata: r.metadata } })}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="font-orbitron text-[9px] text-hud-cyan/40">#{i + 1}</span>
                    <div className="h-1.5 rounded-full" style={{ width: `${Math.round(r.similarity * 100)}px`, maxWidth: '60px', background: r.similarity > 0.8 ? '#30d158' : r.similarity > 0.5 ? '#ff9f0a' : '#636366' }} />
                    <span className="font-mono-tech text-[8px]" style={{ color: r.similarity > 0.8 ? '#30d158' : r.similarity > 0.5 ? '#ff9f0a' : '#636366' }}>
                      {Math.round(r.similarity * 100)}% match
                    </span>
                  </div>
                  <button onClick={e => { e.stopPropagation(); deleteDoc(r.id); }} className="text-hud-red/30 hover:text-hud-red transition-colors">
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
            {!loading && !query && (
              <div className="flex flex-col items-center justify-center h-32" style={{ color: `${ACCENT}30` }}>
                <Brain size={28} className="mb-2 opacity-40" />
                <span className="font-orbitron text-[9px]">VECTOR MEMORY SEARCH</span>
                <span className="font-mono-tech text-[8px] mt-1 opacity-60">POWERED BY CHROMADB</span>
              </div>
            )}
          </>
        )}

        {subTab === 'index' && (
          <div className="flex flex-col gap-3">
            <textarea value={indexText} onChange={e => setIndexText(e.target.value)}
              placeholder="ENTER TEXT TO INDEX INTO VECTOR MEMORY..."
              rows={6}
              className="w-full bg-transparent border border-hud-cyan/20 rounded px-2 py-1.5 font-mono-tech text-[9px] text-hud-cyan placeholder:text-hud-cyan/30 outline-none focus:border-hud-cyan/50 resize-none"
            />
            <input value={indexMeta} onChange={e => setIndexMeta(e.target.value)}
              placeholder='METADATA JSON e.g. {"source":"manual"}'
              className="w-full bg-transparent border border-hud-cyan/20 rounded px-2 py-1.5 font-mono-tech text-[8px] text-hud-cyan placeholder:text-hud-cyan/30 outline-none focus:border-hud-cyan/50"
            />
            <div className="flex gap-2">
              <button onClick={doIndex} disabled={loading || !indexText.trim()}
                className="flex-1 flex items-center justify-center gap-1 font-orbitron text-[8px] px-2 py-1.5 rounded border transition-all disabled:opacity-40"
                style={{ borderColor: `${ACCENT}60`, color: ACCENT }}
              >
                <Plus size={10} /> INDEX DOCUMENT
              </button>
              <button onClick={indexKB} disabled={loading}
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

        {subTab === 'stats' && (
          <div className="flex flex-col gap-3">
            {stats ? (
              <>
                <div className="hud-panel rounded p-3 text-center">
                  <div className="font-orbitron text-2xl font-bold" style={{ color: ACCENT }}>{stats.total_documents}</div>
                  <div className="font-orbitron text-[8px] text-hud-cyan/50 mt-1">TOTAL VECTORS</div>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  {COLLECTIONS.map(c => (
                    <div key={c.id} className="hud-panel rounded p-3" style={{ borderLeft: `3px solid ${c.color}` }}>
                      <div className="font-orbitron text-lg font-bold" style={{ color: c.color }}>{stats.collections[c.id] ?? 0}</div>
                      <div className="font-orbitron text-[7px] text-hud-cyan/40 mt-0.5">{c.label}</div>
                    </div>
                  ))}
                </div>
                <div className="flex items-center gap-2 mt-1">
                  <Database size={10} className="text-hud-cyan/40" />
                  <span className="font-mono-tech text-[8px] text-hud-cyan/40">ChromaDB · PersistentClient · spark_memory_db/</span>
                </div>
              </>
            ) : (
              <div className="flex items-center justify-center h-32">
                <button onClick={loadStats}
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

// ═══════════════════════════════════════════════════════════════════════════
// REMINDERS TAB
// ═══════════════════════════════════════════════════════════════════════════
function RemindersTab() {
  const { reminders, status, history, isLoading, createReminder, deleteReminder, toggleReminder, isCreating } = useScheduler();
  const [subTab, setSubTab] = useState<'reminders' | 'history'>('reminders');

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="px-3 pt-2 pb-2 shrink-0 flex items-center justify-between">
        <div className="flex gap-1">
          {(['reminders', 'history'] as const).map(t => (
            <button key={t} onClick={() => setSubTab(t)}
              className="flex items-center gap-1 font-orbitron text-[8px] px-2 py-1 rounded border transition-all"
              style={{
                borderColor: subTab === t ? ACCENT : `${ACCENT}30`,
                color: subTab === t ? ACCENT : `${ACCENT}50`,
                background: subTab === t ? `${ACCENT}15` : 'transparent',
              }}
            >
              {t === 'reminders' ? <Bell size={9} /> : <History size={9} />}
              {t.toUpperCase()}
              {t === 'reminders' && <span style={{ opacity: 0.6 }}>({reminders.length})</span>}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          {isLoading && <Loader2 size={12} className="animate-spin" style={{ color: `${ACCENT}80` }} />}
          {status && (
            <div className={`flex items-center gap-1 font-orbitron text-[8px] px-2 py-0.5 rounded border ${status.running ? 'border-hud-green/40 text-hud-green' : 'border-hud-red/40 text-hud-red'}`}>
              <div className={`w-1.5 h-1.5 rounded-full ${status.running ? 'bg-hud-green animate-pulse' : 'bg-hud-red'}`} />
              {status.running ? 'RUNNING' : 'STOPPED'} · {status.job_count}
            </div>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto scrollbar-hud p-3 flex flex-col gap-2">
        {subTab === 'reminders' && (
          <>
            <CreateReminderForm onSubmit={createReminder} isCreating={isCreating} />
            {reminders.length === 0 && !isLoading && (
              <div className="flex flex-col items-center justify-center h-32" style={{ color: `${ACCENT}30` }}>
                <Calendar size={24} className="mb-2 opacity-40" />
                <span className="font-orbitron text-[9px]">NO REMINDERS SET</span>
              </div>
            )}
            {reminders.map(r => (
              <ReminderCard key={r.id} reminder={r} onDelete={deleteReminder} onToggle={toggleReminder} />
            ))}
          </>
        )}
        {subTab === 'history' && (
          <>
            {history.length === 0 ? (
              <div className="flex items-center justify-center h-32" style={{ color: `${ACCENT}30` }}>
                <span className="font-orbitron text-[9px]">NO HISTORY YET</span>
              </div>
            ) : history.map((h, i) => (
              <div key={i} className="hud-panel rounded p-2 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <CheckCircle size={10} className="text-hud-green/60" />
                  <span className="font-orbitron text-[9px] text-hud-cyan">{h.title}</span>
                </div>
                <span className="font-mono-tech text-[8px] text-hud-cyan/40">
                  {new Date(h.fired_at).toLocaleString()}
                </span>
              </div>
            ))}
          </>
        )}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// MindModule — main export
// ═══════════════════════════════════════════════════════════════════════════
export default function MindModule() {
  const [tab, setTab] = useState<'search' | 'reminders'>('search');

  const tabs = [
    { id: 'search' as const,    label: 'SEARCH',    icon: <Brain size={11} /> },
    { id: 'reminders' as const, label: 'REMINDERS', icon: <Clock size={11} /> },
  ];

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Tab bar */}
      <div className="flex items-center gap-0 border-b shrink-0" style={{ borderColor: `${ACCENT}20` }}>
        <div className="flex items-center gap-1 px-3 py-1 shrink-0">
          <BarChart2 size={12} style={{ color: ACCENT }} />
          <span className="font-orbitron text-[9px] tracking-widest" style={{ color: `${ACCENT}80` }}>MIND</span>
        </div>
        <div className="w-px h-5 mx-1" style={{ background: `${ACCENT}20` }} />
        {tabs.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className="relative flex items-center gap-1.5 px-4 py-2 font-orbitron text-[9px] tracking-wider transition-all"
            style={{ color: tab === t.id ? ACCENT : `${ACCENT}40` }}
          >
            {t.icon}
            {t.label}
            {tab === t.id && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 rounded-t-full" style={{ background: ACCENT }} />
            )}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {tab === 'search'    && <SearchTab />}
        {tab === 'reminders' && <RemindersTab />}
      </div>
    </div>
  );
}
