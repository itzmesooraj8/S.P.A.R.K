/**
 * PasswordAuditPanel — Combat Mode Password / Hash Audit Lab
 * Provides: hash file analysis, CUPP wordlist generation, hashcat job launch
 */
import React, { useState, useCallback, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useCombatStore } from '../../store/useCombatStore'

const API = (path: string) => `http://${window.location.hostname}:8000${path}`

const RISK_COLOR: Record<string, string> = {
  LOW:      '#34d399',
  MEDIUM:   '#FF9F0A',
  HIGH:     '#FF6B35',
  CRITICAL: '#FF2D55',
  UNKNOWN:  '#555',
}

type StrengthReport = {
  file_path:         string
  total_hashes:      number
  detected_format:   string
  blank_passwords:   number
  policy_violations: number
  unique_hashes:     number
  duplicate_count:   number
  risk_level:        string
  recommendations:   string[]
}

type HashcatJob = {
  job_id:         string
  hash_type:      string
  status:         string
  recovered:      number
  total:          number
  progress_pct:   number
  speed_hps:      number
  time_remaining: string
  output_file:    string
}

type Tab = 'analyze' | 'cupp' | 'hashcat'

const PasswordAuditPanel: React.FC = () => {
  const { sessionToken } = useCombatStore()
  const [tab, setTab] = useState<Tab>('analyze')

  // Analyze tab
  const [analyzeFile, setAnalyzeFile] = useState('')
  const [report, setReport] = useState<StrengthReport | null>(null)
  const [analyzing, setAnalyzing] = useState(false)

  // CUPP tab
  const [cuppFields, setCuppFields] = useState({
    first_name: '', last_name: '', nickname: '', birthdate: '',
    partner: '', pet_name: '', company: '', keywords: '',
  })
  const [cuppResult, setCuppResult] = useState<{ wordlist_path: string; line_count: number; status: string } | null>(null)
  const [cuppRunning, setCuppRunning] = useState(false)

  // Hashcat tab
  const [hcFile, setHcFile] = useState('')
  const [hcWordlist, setHcWordlist] = useState('')
  const [hcType, setHcType] = useState('ntlm')
  const [hcJob, setHcJob] = useState<HashcatJob | null>(null)
  const [hcRunning, setHcRunning] = useState(false)

  const [error, setError] = useState('')

  // Real-time hashcat progress via combat WS
  useEffect(() => {
    const handler = (e: Event) => {
      const msg = (e as CustomEvent).detail as Record<string, unknown>
      if (msg?.type === 'HASHCAT_PROGRESS') {
        setHcJob(prev => prev ? { ...prev, ...(msg as unknown as Partial<HashcatJob>) } : null)
      }
    }
    window.addEventListener('spark:ws', handler)
    return () => window.removeEventListener('spark:ws', handler)
  }, [])

  const analyzeFile_ = useCallback(async () => {
    setAnalyzing(true); setError(''); setReport(null)
    try {
      const res = await fetch(API('/api/combat/auth/strength'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Combat-Token': sessionToken! },
        body: JSON.stringify({ file_path: analyzeFile }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Analysis failed')
      setReport(data)
    } catch (e: unknown) { setError(e instanceof Error ? e.message : String(e)) }
    finally { setAnalyzing(false) }
  }, [analyzeFile, sessionToken])

  const runCupp = useCallback(async () => {
    setCuppRunning(true); setError(''); setCuppResult(null)
    try {
      const res = await fetch(API('/api/combat/auth/cupp'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Combat-Token': sessionToken! },
        body: JSON.stringify({
          ...cuppFields,
          keywords: cuppFields.keywords.split(',').map(k => k.trim()).filter(Boolean),
        }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'CUPP failed')
      setCuppResult(data)
    } catch (e: unknown) { setError(e instanceof Error ? e.message : String(e)) }
    finally { setCuppRunning(false) }
  }, [cuppFields, sessionToken])

  const runHashcat = useCallback(async () => {
    setHcRunning(true); setError(''); setHcJob(null)
    try {
      const res = await fetch(API('/api/combat/auth/hashcat'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Combat-Token': sessionToken! },
        body: JSON.stringify({ hash_file: hcFile, wordlist: hcWordlist, hash_type: hcType }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Hashcat failed')
      setHcJob(data)
    } catch (e: unknown) { setError(e instanceof Error ? e.message : String(e)) }
    finally { setHcRunning(false) }
  }, [hcFile, hcWordlist, hcType, sessionToken])

  const inputStyle: React.CSSProperties = {
    background: '#19050c', border: '1px solid #3a1520', borderRadius: 4,
    padding: '6px 10px', color: '#fff', fontSize: 12, width: '100%', boxSizing: 'border-box',
  }

  const btnStyle = (active?: boolean): React.CSSProperties => ({
    background: active ? '#FF2D55' : 'transparent',
    border: active ? 'none' : '1px solid #3a1520',
    borderRadius: 4, padding: '5px 14px', color: active ? '#fff' : '#888',
    fontSize: 11, fontWeight: 700, cursor: 'pointer', letterSpacing: 1,
  })

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10, height: '100%' }}>
      {/* Tabs */}
      <div style={{ display: 'flex', gap: 8, borderBottom: '1px solid #2a0010', paddingBottom: 8 }}>
        {(['analyze', 'cupp', 'hashcat'] as Tab[]).map(t => (
          <button key={t} onClick={() => setTab(t)} style={{
            ...btnStyle(tab === t),
            border: 'none',
            borderBottom: tab === t ? '2px solid #FF2D55' : '2px solid transparent',
            borderRadius: 0, background: 'transparent',
            color: tab === t ? '#FF2D55' : '#555', fontSize: 11, letterSpacing: 1.5,
          }}>
            {t === 'analyze' ? 'ANALYZE' : t === 'cupp' ? 'WORDLIST' : 'HASHCAT'}
          </button>
        ))}
      </div>

      {error && (
        <div style={{ color: '#FF2D55', fontSize: 11, padding: '4px 8px',
          background: '#1a0005', borderRadius: 4 }}>
          {error}
        </div>
      )}

      <AnimatePresence mode="wait">
        {/* ── ANALYZE TAB ── */}
        {tab === 'analyze' && (
          <motion.div key="analyze"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            style={{ display: 'flex', flexDirection: 'column', gap: 10, flex: 1 }}
          >
            <div style={{ display: 'flex', gap: 8 }}>
              <input value={analyzeFile} onChange={e => setAnalyzeFile(e.target.value)}
                placeholder="/path/to/hashes.txt" style={{ ...inputStyle, flex: 1 }} />
              <button onClick={analyzeFile_} disabled={analyzing || !analyzeFile} style={btnStyle(true)}>
                {analyzing ? 'ANALYZING…' : 'ANALYZE'}
              </button>
            </div>
            {report && (
              <motion.div initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }}
                style={{ background: '#0d0003', border: '1px solid #3a1520', borderRadius: 6, padding: 12 }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10 }}>
                  <span style={{ color: '#888', fontSize: 11 }}>{report.detected_format}</span>
                  <span style={{ color: RISK_COLOR[report.risk_level], fontWeight: 700, fontSize: 13 }}>
                    {report.risk_level}
                  </span>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, marginBottom: 10 }}>
                  {[
                    ['Total Hashes',   String(report.total_hashes)],
                    ['Unique',         String(report.unique_hashes)],
                    ['Duplicates',     String(report.duplicate_count)],
                    ['Blank Passwords', String(report.blank_passwords)],
                    ['Violations',     String(report.policy_violations)],
                  ].map(([label, val]) => (
                    <div key={label} style={{ background: '#0a0002', borderRadius: 4, padding: '6px 10px' }}>
                      <div style={{ color: '#555', fontSize: 9, letterSpacing: 1 }}>{label}</div>
                      <div style={{ color: '#fff', fontWeight: 700, fontSize: 16 }}>{val}</div>
                    </div>
                  ))}
                </div>
                {report.recommendations.map((r, i) => (
                  <div key={i} style={{ color: '#FF9F0A', fontSize: 11, marginBottom: 4 }}>▸ {r}</div>
                ))}
              </motion.div>
            )}
          </motion.div>
        )}

        {/* ── CUPP TAB ── */}
        {tab === 'cupp' && (
          <motion.div key="cupp"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            style={{ display: 'flex', flexDirection: 'column', gap: 8, flex: 1 }}
          >
            <div style={{ color: '#555', fontSize: 10, letterSpacing: 1 }}>
              TARGET PROFILE (leave blank fields you don't know)
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
              {Object.entries(cuppFields).map(([key, val]) => (
                <input key={key}
                  value={val}
                  onChange={e => setCuppFields(p => ({ ...p, [key]: e.target.value }))}
                  placeholder={key.replace('_', ' ')}
                  style={inputStyle}
                />
              ))}
            </div>
            <button onClick={runCupp} disabled={cuppRunning} style={{ ...btnStyle(true), alignSelf: 'flex-start' }}>
              {cuppRunning ? 'GENERATING…' : 'GENERATE WORDLIST'}
            </button>
            {cuppResult && (
              <div style={{ color: cuppResult.status === 'COMPLETE' ? '#34d399' : '#FF9F0A', fontSize: 12 }}>
                ✓ {cuppResult.line_count.toLocaleString()} words →{' '}
                <span style={{ color: '#555', fontFamily: 'monospace', fontSize: 11 }}>
                  {cuppResult.wordlist_path}
                </span>
              </div>
            )}
          </motion.div>
        )}

        {/* ── HASHCAT TAB ── */}
        {tab === 'hashcat' && (
          <motion.div key="hashcat"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            style={{ display: 'flex', flexDirection: 'column', gap: 8, flex: 1 }}
          >
            <div style={{ color: '#555', fontSize: 10, letterSpacing: 1 }}>
              DICTIONARY ATTACK — AUTHORISED HASHES ONLY
            </div>
            <input value={hcFile} onChange={e => setHcFile(e.target.value)}
              placeholder="Hash file path" style={inputStyle} />
            <input value={hcWordlist} onChange={e => setHcWordlist(e.target.value)}
              placeholder="Wordlist path" style={inputStyle} />
            <select value={hcType} onChange={e => setHcType(e.target.value)}
              style={{ ...inputStyle }}>
              {['ntlm', 'md5', 'sha1', 'sha256', 'sha512', 'bcrypt', 'wpa2', 'netntlmv2'].map(t => (
                <option key={t} value={t}>{t.toUpperCase()}</option>
              ))}
            </select>
            <button onClick={runHashcat} disabled={hcRunning || !hcFile || !hcWordlist}
              style={{ ...btnStyle(true), alignSelf: 'flex-start' }}>
              {hcRunning ? 'CRACKING…' : 'RUN HASHCAT'}
            </button>
            {hcJob && (
              <div style={{ background: '#0d0003', border: '1px solid #3a1520', borderRadius: 6, padding: 12 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                  <span style={{ color: '#888', fontSize: 11 }}>Job {hcJob.job_id}</span>
                  <span style={{ color: '#34d399', fontSize: 11, fontWeight: 700 }}>{hcJob.status}</span>
                </div>
                {/* Progress bar */}
                <div style={{ background: '#2a0010', borderRadius: 2, height: 4, marginBottom: 8 }}>
                  <div style={{ background: '#FF2D55', width: `${hcJob.progress_pct}%`, height: '100%', borderRadius: 2, transition: 'width 0.5s' }} />
                </div>
                <div style={{ display: 'flex', gap: 16, fontSize: 11, color: '#888' }}>
                  <span>Recovered: <b style={{ color: '#fff' }}>{hcJob.recovered}/{hcJob.total}</b></span>
                  <span>Speed: <b style={{ color: '#fff' }}>{(hcJob.speed_hps / 1e6).toFixed(1)} MH/s</b></span>
                  <span>ETA: <b style={{ color: '#fff' }}>{hcJob.time_remaining}</b></span>
                </div>
                <div style={{ color: '#555', fontSize: 10, marginTop: 8 }}>
                  Results saved to: {hcJob.output_file}
                </div>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default PasswordAuditPanel
