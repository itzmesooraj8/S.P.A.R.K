import React, { useState, useCallback } from 'react'
import { motion } from 'framer-motion'
import { useCombatStore } from '../../store/useCombatStore'

// ─── Feed shape types ────────────────────────────────────────────────────────
interface CisaEntry  { cveID: string; vulnerabilityName: string }
interface NvdItem    { severity: string; base_score: number; description: string }
interface FeedPayload {
  feeds: {
    cisa_kev?: { total: number; recent: CisaEntry[] }
    nvd?:      { total_results: number; items: NvdItem[] }
  }
}
interface CveRow {
  cve_id:      string
  severity:    string
  base_score:  number | null
  description: string
}
interface SentimentResult {
  parsed?: {
    threat_level?:            string
    likelihood?:              string
    exploitation_likelihood?: number
    active_exploitation?:     boolean
    analyst_summary?:         string
    recommended_actions?:     string[]
    summary?:                 string
  }
  raw?: string
}

const API = (path: string) => `http://${window.location.hostname}:8000${path}`

const BTN: React.CSSProperties = {
  background:   '#FF2D55',
  border:       'none',
  borderRadius: 6,
  padding:      '7px 14px',
  color:        '#fff',
  fontSize:     11,
  fontWeight:   700,
  cursor:       'pointer',
  letterSpacing: 1,
}

const INPUT: React.CSSProperties = {
  background:   '#19050c',
  border:       '1px solid #3a1520',
  borderRadius: 6,
  padding:      '7px 10px',
  color:        '#fff',
  fontSize:     12,
  outline:      'none',
}

const SEVERITY_COLOR: Record<string, string> = {
  CRITICAL: '#FF2D55',
  HIGH:     '#FF6B35',
  MEDIUM:   '#FFB020',
  LOW:      '#4CAF50',
}

const TAB_STYLE = (active: boolean) => ({
  padding:      '6px 14px',
  fontSize:     11,
  letterSpacing: 1.5,
  cursor:       'pointer',
  border:       'none',
  borderBottom: active ? '2px solid #FF2D55' : '2px solid transparent',
  background:   'transparent',
  color:        active ? '#FF2D55' : '#555',
  transition:   'all 0.2s',
})

// ─────────────────────────────────────────────────────────────────────────────
// SIGINT Feed sub-panel
// ─────────────────────────────────────────────────────────────────────────────

const FeedView: React.FC = () => {
  const { sessionToken, sigintFeeds, sigintLoading, setSigintFeeds, setSigintLoading } = useCombatStore()

  const fetchFeeds = useCallback(async () => {
    if (!sessionToken) return
    setSigintLoading(true)
    try {
      const r = await fetch(API('/api/combat/sigint/feeds'), {
        headers: { 'X-Combat-Token': sessionToken },
      })
      setSigintFeeds(await r.json())
    } finally {
      setSigintLoading(false)
    }
  }, [sessionToken, setSigintFeeds, setSigintLoading])

  const feeds = sigintFeeds as unknown as FeedPayload | null

  return (
    <div style={{ padding: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
        <span style={{ fontSize: 11, color: '#FF2D55', letterSpacing: 2 }}>LIVE THREAT FEEDS</span>
        <button style={BTN} onClick={fetchFeeds} disabled={sigintLoading}>
          {sigintLoading ? 'FETCHING…' : 'REFRESH'}
        </button>
      </div>

      {!feeds && !sigintLoading && (
        <div style={{ textAlign: 'center', color: '#444', fontSize: 12, padding: '30px 0' }}>
          Click REFRESH to pull threat intelligence feeds.
        </div>
      )}

      {feeds && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {/* CISA KEV */}
          {feeds?.feeds?.cisa_kev && (
            <div style={{ background: '#0d0408', borderRadius: 6, padding: 12 }}>
              <div style={{ fontSize: 11, color: '#FF2D55', letterSpacing: 1, marginBottom: 8 }}>
                ◈ CISA KEV — {feeds.feeds.cisa_kev.total} Total Exploited CVEs
              </div>
              {(feeds.feeds.cisa_kev.recent || []).slice(0, 8).map((v: CisaEntry, i: number) => (
                <div key={i} style={{ fontSize: 11, color: '#ccc', padding: '3px 0', borderBottom: '1px solid #1a0810' }}>
                  <span style={{ color: '#FF6B35', marginRight: 8 }}>{v.cveID}</span>
                  {v.vulnerabilityName}
                </div>
              ))}
            </div>
          )}

          {/* NVD */}
          {feeds?.feeds?.nvd?.items && (
            <div style={{ background: '#0d0408', borderRadius: 6, padding: 12 }}>
              <div style={{ fontSize: 11, color: '#FF2D55', letterSpacing: 1, marginBottom: 8 }}>
                ◈ NVD — {feeds.feeds.nvd.total_results} Total Results
              </div>
              {(feeds.feeds.nvd.items || []).slice(0, 8).map((v: NvdItem, i: number) => (
                <div key={i} style={{ fontSize: 11, color: '#ccc', padding: '3px 0', borderBottom: '1px solid #1a0810', display:'flex', gap:8, alignItems:'flex-start' }}>
                  <span style={{ color: SEVERITY_COLOR[v.severity] || '#888', minWidth: 70, flexShrink:0 }}>
                    {v.base_score ? `${v.base_score} ${v.severity}` : 'N/A'}
                  </span>
                  <span style={{ flex:1 }}>{v.description?.slice(0,120)}…</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// CVE Search sub-panel
// ─────────────────────────────────────────────────────────────────────────────

const CveSearch: React.FC = () => {
  const { sessionToken } = useCombatStore()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<CveRow[]>([])
  const [loading, setLoading] = useState(false)
  const [syncing, setSyncing] = useState(false)

  const search = async () => {
    if (!sessionToken) return
    setLoading(true)
    try {
      const r = await fetch(API(`/api/combat/sigint/cve?q=${encodeURIComponent(query)}&limit=50`), {
        headers: { 'X-Combat-Token': sessionToken },
      })
      const d = await r.json()
      setResults(Array.isArray(d) ? d : [])
    } finally { setLoading(false) }
  }

  const triggerSync = async () => {
    if (!sessionToken) return
    setSyncing(true)
    await fetch(API('/api/combat/sigint/cve/sync'), {
      method: 'POST', headers: { 'X-Combat-Token': sessionToken },
    })
    setTimeout(() => setSyncing(false), 3000)
  }

  return (
    <div style={{ padding: 16 }}>
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <input style={{ ...INPUT, flex: 1 }} placeholder="Search CVEs…"
          value={query} onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && search()} />
        <button style={BTN} onClick={search} disabled={loading}>
          {loading ? '…' : 'SEARCH'}
        </button>
        <button style={{ ...BTN, background: '#3a1520' }} onClick={triggerSync} disabled={syncing}
          title="Sync NVD database locally">
          {syncing ? 'SYNCING…' : 'SYNC DB'}
        </button>
      </div>
      <div style={{ maxHeight: 300, overflowY: 'auto' }}>
        {results.map((row, i) => (
          <div key={i} style={{ fontSize:11, padding:'5px 0', borderBottom:'1px solid #1a0810', display:'flex', gap:8 }}>
            <span style={{ color: SEVERITY_COLOR[row.severity] || '#666', minWidth: 75, flexShrink:0 }}>
              {row.base_score ?? '—'} {row.severity ?? ''}
            </span>
            <span style={{ color:'#FF6B35', minWidth:120, flexShrink:0 }}>{row.cve_id}</span>
            <span style={{ color:'#aaa', flex:1 }}>{row.description?.slice(0,140)}</span>
          </div>
        ))}
        {results.length === 0 && !loading && (
          <div style={{ color:'#333', fontSize:11, textAlign:'center', padding:'20px 0' }}>
            No results. Sync the NVD database first if the index is empty.
          </div>
        )}
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Sentiment Analysis sub-panel
// ─────────────────────────────────────────────────────────────────────────────

const SentimentView: React.FC = () => {
  const { sessionToken } = useCombatStore()
  const [topic, setTopic] = useState('')
  const [result, setResult] = useState<SentimentResult | null>(null)
  const [loading, setLoading] = useState(false)

  const analyze = async () => {
    if (!topic.trim() || !sessionToken) return
    setLoading(true)
    try {
      const r = await fetch(API(`/api/combat/sigint/sentiment?topic=${encodeURIComponent(topic)}`), {
        headers: { 'X-Combat-Token': sessionToken },
      })
      setResult(await r.json())
    } finally { setLoading(false) }
  }

  const parsed = result?.parsed

  return (
    <div style={{ padding: 16 }}>
      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        <input style={{ ...INPUT, flex: 1 }} placeholder="CVE-YYYY-NNNNN or technology keyword…"
          value={topic} onChange={(e) => setTopic(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && analyze()} />
        <button style={BTN} onClick={analyze} disabled={loading}>
          {loading ? 'ANALYSING…' : 'ANALYSE'}
        </button>
      </div>
      {parsed && (
        <div style={{ background:'#0d0408', borderRadius:8, padding:14, fontSize:12 }}>
          <div style={{ display:'flex', gap:16, marginBottom:12, alignItems:'center' }}>
            <span style={{
              padding:'4px 12px', borderRadius:4, fontSize:11, fontWeight:700,
              background: SEVERITY_COLOR[parsed.threat_level] || '#333',
              color: '#fff',
            }}>
              {parsed.threat_level}
            </span>
            <span style={{ color:'#aaa' }}>
              Exploitation Likelihood: <strong style={{ color:'#FF6B35' }}>{parsed.exploitation_likelihood}%</strong>
            </span>
            {parsed.active_exploitation && (
              <span style={{ color:'#FF2D55', fontWeight:700, fontSize:11 }}>⚠ ACTIVE EXPLOITATION</span>
            )}
          </div>
          <p style={{ color:'#ccc', margin:'0 0 10px', lineHeight:1.6 }}>{parsed.analyst_summary}</p>
          {parsed.recommended_actions?.length > 0 && (
            <div>
              <div style={{ fontSize:10, color:'#FF2D55', letterSpacing:2, marginBottom:6 }}>RECOMMENDED ACTIONS</div>
              {parsed.recommended_actions.map((a: string, i: number) => (
                <div key={i} style={{ fontSize:11, color:'#999', padding:'2px 0' }}>→ {a}</div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Main SigintPanel
// ─────────────────────────────────────────────────────────────────────────────

type SigintTab = 'feeds' | 'cve' | 'sentiment'

export const SigintPanel: React.FC = () => {
  const [tab, setTab] = useState<SigintTab>('feeds')
  const isActive = useCombatStore((s) => s.isActive)

  if (!isActive) return null

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      style={{
        background:   '#0F0508',
        border:       '1px solid #3a0f1e',
        borderRadius: 10,
        overflow:     'hidden',
        minWidth:     480,
      }}
    >
      <div style={{
        display:'flex', alignItems:'center', borderBottom:'1px solid #1f0a12',
        padding:'10px 20px', gap:8,
      }}>
        <span style={{ fontSize:10, letterSpacing:3, color:'#FF2D55', fontWeight:700 }}>◈</span>
        <span style={{ fontSize:12, color:'#fff', fontWeight:700, letterSpacing:2 }}>SIGINT FEED</span>
        <div style={{ marginLeft:'auto', display:'flex', gap:0 }}>
          {(['feeds', 'cve', 'sentiment'] as const).map((t) => (
            <button key={t} style={TAB_STYLE(tab === t)} onClick={() => setTab(t)}>
              {t === 'feeds' ? 'FEEDS' : t === 'cve' ? 'CVE INDEX' : 'SENTIMENT'}
            </button>
          ))}
        </div>
      </div>
      {tab === 'feeds'     && <FeedView />}
      {tab === 'cve'       && <CveSearch />}
      {tab === 'sentiment' && <SentimentView />}
    </motion.div>
  )
}
