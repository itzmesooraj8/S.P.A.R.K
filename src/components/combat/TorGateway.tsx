import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { useCombatStore } from '../../store/useCombatStore'

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

const VERDICT_COLOR: Record<string, string> = {
  TRUSTED:      '#4CAF50',
  LIKELY_SAFE:  '#8BC34A',
  UNKNOWN:      '#FFB020',
  CAUTION:      '#FF2D55',
}

interface OnionSite {
  name:            string
  url:             string
  category:        string
  description:     string
  clearweb_mirror?: string
  trust_score:     number
}

interface VerifyResult {
  url:           string
  trust_score:   number
  in_registry:   boolean
  verdict:       string
  reachability?: Record<string, unknown>
  registry_entry?: OnionSite
}

export const TorGateway: React.FC = () => {
  const { sessionToken } = useCombatStore()
  const [registry, setRegistry]     = useState<OnionSite[]>([])
  const [loadingReg, setLoadingReg] = useState(false)
  const [verifyUrl, setVerifyUrl]   = useState('')
  const [verifyResult, setVerifyResult] = useState<VerifyResult | null>(null)
  const [verifying, setVerifying]   = useState(false)
  const isActive = useCombatStore((s) => s.isActive)

  const fetchRegistry = async () => {
    if (!sessionToken) return
    setLoadingReg(true)
    try {
      const r = await fetch(API('/api/combat/tor/registry'), {
        headers: { 'X-Combat-Token': sessionToken },
      })
      const d = await r.json()
      setRegistry(d.sites || [])
    } finally { setLoadingReg(false) }
  }

  const verifySite = async () => {
    if (!verifyUrl.trim() || !sessionToken) return
    setVerifying(true)
    setVerifyResult(null)
    try {
      const r = await fetch(API('/api/combat/tor/verify'), {
        method:  'POST',
        headers: { 'Content-Type': 'application/json', 'X-Combat-Token': sessionToken },
        body:    JSON.stringify({ url: verifyUrl.trim() }),
      })
      setVerifyResult(await r.json())
    } finally { setVerifying(false) }
  }

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
        minWidth:     460,
      }}
    >
      <div style={{
        display:'flex', alignItems:'center', borderBottom:'1px solid #1f0a12',
        padding:'10px 20px', gap:8,
      }}>
        <span style={{ fontSize:10, letterSpacing:3, color:'#FF2D55', fontWeight:700 }}>◈</span>
        <span style={{ fontSize:12, color:'#fff', fontWeight:700, letterSpacing:2 }}>TOR GATEWAY</span>
        <span style={{ marginLeft:'auto', fontSize:10, color:'#444' }}>RESEARCH USE ONLY</span>
      </div>

      <div style={{ padding: 16 }}>
        {/* Site verifier */}
        <div style={{ marginBottom: 20 }}>
          <div style={{ fontSize:11, color:'#FF2D55', letterSpacing:2, marginBottom:10 }}>SITE TRUST VERIFIER</div>
          <div style={{ display:'flex', gap:8 }}>
            <input style={{ ...INPUT, flex:1 }} placeholder="https://example.onion"
              value={verifyUrl} onChange={(e) => setVerifyUrl(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && verifySite()} />
            <button style={BTN} onClick={verifySite} disabled={verifying}>
              {verifying ? 'CHECKING…' : 'VERIFY'}
            </button>
          </div>

          {verifyResult && (
            <div style={{ marginTop:12, background:'#0d0408', borderRadius:6, padding:12 }}>
              <div style={{ display:'flex', alignItems:'center', gap:12, marginBottom:8 }}>
                <span style={{
                  padding:'3px 10px', borderRadius:4, fontSize:11, fontWeight:700,
                  background: VERDICT_COLOR[verifyResult.verdict] || '#333', color:'#fff',
                }}>
                  {verifyResult.verdict}
                </span>
                <span style={{ fontSize:12, color:'#aaa' }}>
                  Trust Score: <strong style={{ color:'#fff' }}>{verifyResult.trust_score}/100</strong>
                </span>
                {verifyResult.in_registry && (
                  <span style={{ fontSize:10, color:'#4CAF50' }}>✓ IN VETTED REGISTRY</span>
                )}
              </div>
              {verifyResult.registry_entry && (
                <div style={{ fontSize:11, color:'#999' }}>
                  <strong style={{ color:'#fff' }}>{verifyResult.registry_entry.name}</strong>
                  {' — '}{verifyResult.registry_entry.description}
                </div>
              )}
              {verifyResult.reachability && (
                <div style={{ fontSize:10, color:'#555', marginTop:6 }}>
                  {verifyResult.reachability.reachable === true
                    ? `✓ Reachable via Tor · ${verifyResult.reachability.latency_ms}ms`
                    : verifyResult.reachability.reachable === false
                    ? `✗ Not reachable · ${verifyResult.reachability.reason}`
                    : 'Reachability check unavailable (httpx[socks] required)'}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Curated registry */}
        <div>
          <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:10 }}>
            <span style={{ fontSize:11, color:'#FF2D55', letterSpacing:2 }}>VETTED ONION REGISTRY</span>
            <button style={{ ...BTN, padding:'5px 12px' }} onClick={fetchRegistry} disabled={loadingReg}>
              {loadingReg ? '…' : 'LOAD'}
            </button>
          </div>
          {registry.length > 0 && (
            <div style={{ display:'flex', flexDirection:'column', gap:6, maxHeight:300, overflowY:'auto' }}>
              {registry.map((site, i) => (
                <div key={i} style={{ background:'#0d0408', borderRadius:6, padding:'8px 12px', fontSize:11 }}>
                  <div style={{ display:'flex', justifyContent:'space-between', marginBottom:4 }}>
                    <strong style={{ color:'#fff' }}>{site.name}</strong>
                    <div style={{ display:'flex', gap:8, alignItems:'center' }}>
                      <span style={{ color:'#666', fontSize:10 }}>{site.category}</span>
                      <span style={{
                        padding:'1px 6px', borderRadius:3, fontSize:10,
                        background: site.trust_score >= 90 ? '#1a3a1a' : site.trust_score >= 70 ? '#2a2a1a' : '#2a1a1a',
                        color:      site.trust_score >= 90 ? '#4f9' : site.trust_score >= 70 ? '#ff9' : '#f99',
                      }}>
                        {site.trust_score}/100
                      </span>
                    </div>
                  </div>
                  <div style={{ color:'#666', marginBottom:4 }}>{site.description}</div>
                  <div style={{ color:'#3a1a2a', fontSize:10, wordBreak:'break-all' }}>{site.url}</div>
                </div>
              ))}
            </div>
          )}
          {registry.length === 0 && (
            <div style={{ color:'#333', fontSize:11, textAlign:'center', padding:'20px 0' }}>
              Click LOAD to view the vetted onion site registry.
            </div>
          )}
        </div>
      </div>
    </motion.div>
  )
}
