import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useCombatStore } from '../../store/useCombatStore'

const API = (path: string) => `http://${window.location.hostname}:8000${path}`

const TAB_STYLE = (active: boolean) => ({
  padding:      '6px 16px',
  fontSize:     11,
  letterSpacing: 1.5,
  fontWeight:   600,
  cursor:       'pointer',
  border:       'none',
  borderBottom: active ? '2px solid #FF2D55' : '2px solid transparent',
  background:   'transparent',
  color:        active ? '#FF2D55' : '#555',
  transition:   'all 0.2s',
})

const INPUT_STYLE: React.CSSProperties = {
  background:   '#19050c',
  border:       '1px solid #3a1520',
  borderRadius: 6,
  padding:      '8px 12px',
  color:        '#fff',
  fontSize:     13,
  outline:      'none',
  width:        '100%',
  boxSizing:    'border-box',
}

const BTN: React.CSSProperties = {
  background:   '#FF2D55',
  border:       'none',
  borderRadius: 6,
  padding:      '8px 18px',
  color:        '#fff',
  fontSize:     12,
  fontWeight:   700,
  cursor:       'pointer',
  letterSpacing: 1,
}

// ─────────────────────────────────────────────────────────────────────────────
// Identity Tab
// ─────────────────────────────────────────────────────────────────────────────

const IdentityTab: React.FC = () => {
  const { sessionToken, huntResults, huntInProgress, clearHuntResults, setHuntJobId } = useCombatStore()
  const [username, setUsername] = useState('')
  const [email,    setEmail]    = useState('')
  const [emailResult, setEmailResult] = useState<Record<string, unknown> | null>(null)
  const [loading,  setLoading]  = useState(false)

  const huntUsername = async () => {
    if (!username.trim() || !sessionToken) return
    clearHuntResults()
    setLoading(true)
    try {
      const r = await fetch(API(`/api/combat/identity/username/${encodeURIComponent(username)}`), {
        headers: { 'X-Combat-Token': sessionToken },
      })
      const d = await r.json()
      setHuntJobId(d.job_id)
    } catch { /* errors appear in WS stream */ }
    finally { setLoading(false) }
  }

  const checkEmail = async () => {
    if (!email.trim() || !sessionToken) return
    setLoading(true)
    try {
      const r = await fetch(API(`/api/combat/identity/email/${encodeURIComponent(email)}`), {
        headers: { 'X-Combat-Token': sessionToken },
      })
      setEmailResult(await r.json())
    } catch { setEmailResult({ error: 'Request failed' }) }
    finally { setLoading(false) }
  }

  return (
    <div style={{ padding: 20 }}>
      {/* Username hunt */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ fontSize: 11, color: '#FF2D55', letterSpacing: 2, marginBottom: 10 }}>
          USERNAME HUNT — SHERLOCK
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <input
            style={INPUT_STYLE}
            placeholder="Target username…"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && huntUsername()}
          />
          <button style={BTN} onClick={huntUsername} disabled={loading || huntInProgress}>
            {huntInProgress ? 'HUNTING…' : 'HUNT'}
          </button>
        </div>
        {huntResults.length > 0 && (
          <div style={{ marginTop: 12, maxHeight: 200, overflowY: 'auto' }}>
            {huntResults.map((hit, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                style={{ display: 'flex', gap: 12, padding: '4px 0', borderBottom: '1px solid #1f0a12', fontSize: 12 }}
              >
                <span style={{ color: '#0f0', width: 8 }}>✓</span>
                <span style={{ color: '#fff', flex: 1 }}>{hit.platform}</span>
                <a href={hit.url} target="_blank" rel="noopener noreferrer"
                   style={{ color: '#FF2D55', maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {hit.url}
                </a>
              </motion.div>
            ))}
          </div>
        )}
      </div>

      {/* Email intel */}
      <div>
        <div style={{ fontSize: 11, color: '#FF2D55', letterSpacing: 2, marginBottom: 10 }}>
          EMAIL INTEL — HIBP + HUNTER.IO
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <input
            style={INPUT_STYLE}
            placeholder="target@domain.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && checkEmail()}
            type="email"
          />
          <button style={BTN} onClick={checkEmail} disabled={loading}>
            CHECK
          </button>
        </div>
        {emailResult && (
          <div style={{ marginTop: 12, background: '#0d0408', borderRadius: 6, padding: 12, fontSize: 11, color: '#ccc' }}>
            <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
              {JSON.stringify(emailResult, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Recon Tab
// ─────────────────────────────────────────────────────────────────────────────

const ReconTab: React.FC = () => {
  const { sessionToken, scopeTargets, setScopeTargets, passiveResults, activeResults,
          reconLoading, setReconLoading, setPassiveResults, setActiveResults } = useCombatStore()
  const [newTarget, setNewTarget] = useState('')
  const [scanTarget, setScanTarget] = useState('')
  const [scanType, setScanType] = useState('basic')
  const [activeTab2, setActiveTab2] = useState<'passive' | 'active' | 'scope'>('scope')

  const addTarget = async () => {
    if (!newTarget.trim() || !sessionToken) return
    try {
      const r = await fetch(API('/api/combat/opsec/scope/add'), {
        method:  'POST',
        headers: { 'Content-Type': 'application/json', 'X-Combat-Token': sessionToken },
        body:    JSON.stringify({ target: newTarget.trim() }),
      })
      const d = await r.json()
      setScopeTargets(d.targets || [])
      setNewTarget('')
    } catch { /* show inline */ }
  }

  const runPassive = async () => {
    if (!scanTarget || !sessionToken) return
    setReconLoading(true)
    try {
      const r = await fetch(API('/api/combat/recon/passive'), {
        method:  'POST',
        headers: { 'Content-Type': 'application/json', 'X-Combat-Token': sessionToken },
        body:    JSON.stringify({ target: scanTarget, modules: ['shodan', 'subfinder', 'harvester'] }),
      })
      setPassiveResults(await r.json())
    } finally { setReconLoading(false) }
  }

  const runActive = async () => {
    if (!scanTarget || !sessionToken) return
    setReconLoading(true)
    try {
      const r = await fetch(API('/api/combat/recon/active'), {
        method:  'POST',
        headers: { 'Content-Type': 'application/json', 'X-Combat-Token': sessionToken },
        body:    JSON.stringify({ target: scanTarget, scan_type: scanType }),
      })
      setActiveResults(await r.json())
    } finally { setReconLoading(false) }
  }

  return (
    <div style={{ padding: 20 }}>
      <div style={{ display: 'flex', gap: 0, marginBottom: 16, borderBottom: '1px solid #1f0a12' }}>
        {(['scope', 'passive', 'active'] as const).map((t) => (
          <button key={t} style={TAB_STYLE(activeTab2 === t)} onClick={() => setActiveTab2(t)}>
            {t.toUpperCase()}
          </button>
        ))}
      </div>

      {activeTab2 === 'scope' && (
        <div>
          <div style={{ fontSize: 11, color: '#FF2D55', letterSpacing: 2, marginBottom: 10 }}>ENGAGEMENT SCOPE</div>
          <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
            <input style={INPUT_STYLE} placeholder="Add target (IP, domain, CIDR)…"
              value={newTarget} onChange={(e) => setNewTarget(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && addTarget()} />
            <button style={BTN} onClick={addTarget}>ADD</button>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {scopeTargets.map((t, i) => (
              <span key={i} style={{
                background: '#1f0810', border: '1px solid #3a0f1e', borderRadius: 4,
                padding: '3px 10px', fontSize: 11, color: '#FF9999',
              }}>{t}</span>
            ))}
            {scopeTargets.length === 0 && (
              <span style={{ fontSize: 11, color: '#444' }}>No targets in scope. Add targets before scanning.</span>
            )}
          </div>
        </div>
      )}

      {(activeTab2 === 'passive' || activeTab2 === 'active') && (
        <div>
          <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
            <input style={INPUT_STYLE} placeholder="Target (must be in scope)…"
              value={scanTarget} onChange={(e) => setScanTarget(e.target.value)} />
            {activeTab2 === 'active' && (
              <select value={scanType} onChange={(e) => setScanType(e.target.value)}
                style={{ ...INPUT_STYLE, width: 'auto', minWidth: 100 }}>
                <option value="basic">basic</option>
                <option value="full">full</option>
                <option value="stealth">stealth</option>
                <option value="vuln">vuln</option>
              </select>
            )}
            <button style={BTN}
              onClick={activeTab2 === 'passive' ? runPassive : runActive}
              disabled={reconLoading}>
              {reconLoading ? 'SCANNING…' : 'SCAN'}
            </button>
          </div>
          {(activeTab2 === 'passive' ? passiveResults : activeResults) && (
            <div style={{ background:'#0d0408', borderRadius:6, padding:12, fontSize:11, color:'#ccc', maxHeight:320, overflowY:'auto' }}>
              <pre style={{ margin:0, whiteSpace:'pre-wrap', wordBreak:'break-all' }}>
                {JSON.stringify(activeTab2 === 'passive' ? passiveResults : activeResults, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Main ReconPanel (4 tabs: Identity, Recon, Sigint, Tor)
// ─────────────────────────────────────────────────────────────────────────────

type ReconPanelTab = 'identity' | 'recon'

export const ReconPanel: React.FC = () => {
  const [tab, setTab] = useState<ReconPanelTab>('identity')
  const isActive = useCombatStore((s) => s.isActive)

  if (!isActive) return null

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 20 }}
      style={{
        background:   '#0F0508',
        border:       '1px solid #3a0f1e',
        borderRadius: 10,
        overflow:     'hidden',
        minWidth:     460,
      }}
    >
      {/* Panel header */}
      <div style={{
        display:      'flex',
        alignItems:   'center',
        borderBottom: '1px solid #1f0a12',
        padding:      '10px 20px',
        gap:          8,
      }}>
        <span style={{ fontSize: 10, letterSpacing: 3, color: '#FF2D55', fontWeight: 700 }}>◈</span>
        <span style={{ fontSize: 12, color: '#fff', fontWeight: 700, letterSpacing: 2 }}>RECON ENGINE</span>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 0 }}>
          {(['identity', 'recon'] as const).map((t) => (
            <button key={t} style={TAB_STYLE(tab === t)} onClick={() => setTab(t)}>
              {t === 'identity' ? 'IDENTITY' : 'RECON'}
            </button>
          ))}
        </div>
      </div>

      <AnimatePresence mode="wait">
        <motion.div
          key={tab}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
        >
          {tab === 'identity' && <IdentityTab />}
          {tab === 'recon'    && <ReconTab />}
        </motion.div>
      </AnimatePresence>
    </motion.div>
  )
}
