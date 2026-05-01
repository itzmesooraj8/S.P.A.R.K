import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { useCombatStore } from '../../store/useCombatStore'

const API = (path: string) => `http://${window.location.hostname}:8000${path}`

const INPUT: React.CSSProperties = {
  background:   '#19050c',
  border:       '1px solid #3a1520',
  borderRadius: 6,
  padding:      '7px 10px',
  color:        '#fff',
  fontSize:     12,
  outline:      'none',
}

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

export const VaultPanel: React.FC = () => {
  const { sessionToken } = useCombatStore()
  const [passphrase, setPassphrase] = useState('')
  const [key, setKey]               = useState('')
  const [value, setValue]           = useState('')
  const [keys, setKeys]             = useState<string[]>([])
  const [fetched, setFetched]       = useState<Record<string, string>>({})
  const [status, setStatus]         = useState('')
  const [loading, setLoading]       = useState(false)
  const isActive = useCombatStore((s) => s.isActive)

  const storeSecret = async () => {
    if (!key || !value || !passphrase || !sessionToken) {
      setStatus('All fields required.')
      return
    }
    setLoading(true)
    try {
      const r = await fetch(API('/api/combat/vault/set'), {
        method:  'POST',
        headers: { 'Content-Type': 'application/json', 'X-Combat-Token': sessionToken },
        body:    JSON.stringify({ key, value, passphrase }),
      })
      const d = await r.json()
      setStatus(r.ok ? `✓ Stored: ${d.key}` : `✗ ${d.detail}`)
      if (r.ok) { setKey(''); setValue('') }
    } catch { setStatus('✗ Network error') }
    finally { setLoading(false) }
  }

  const listKeys = async () => {
    if (!passphrase || !sessionToken) { setStatus('Enter passphrase first.'); return }
    setLoading(true)
    try {
      const r = await fetch(API('/api/combat/vault/list'), {
        method:  'POST',
        headers: { 'Content-Type': 'application/json', 'X-Combat-Token': sessionToken },
        body:    JSON.stringify({ passphrase }),
      })
      const d = await r.json()
      if (r.ok) setKeys(d.keys || [])
      else setStatus(`✗ ${d.detail}`)
    } catch { setStatus('✗ Network error') }
    finally { setLoading(false) }
  }

  const fetchSecret = async (k: string) => {
    if (!passphrase || !sessionToken) return
    try {
      const r = await fetch(API('/api/combat/vault/get'), {
        method:  'POST',
        headers: { 'Content-Type': 'application/json', 'X-Combat-Token': sessionToken },
        body:    JSON.stringify({ key: k, passphrase }),
      })
      const d = await r.json()
      if (r.ok) setFetched((prev) => ({ ...prev, [k]: d.value }))
    } catch { /* inline */ }
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
        minWidth:     420,
      }}
    >
      <div style={{
        display:'flex', alignItems:'center', borderBottom:'1px solid #1f0a12',
        padding:'10px 20px', gap:8,
      }}>
        <span style={{ fontSize:10, letterSpacing:3, color:'#FF2D55', fontWeight:700 }}>◈</span>
        <span style={{ fontSize:12, color:'#fff', fontWeight:700, letterSpacing:2 }}>API KEY VAULT</span>
        <span style={{ marginLeft:'auto', fontSize:10, color:'#444' }}>AES-256-GCM</span>
      </div>

      <div style={{ padding:16, display:'flex', flexDirection:'column', gap:14 }}>
        {/* Vault passphrase */}
        <div>
          <label style={{ fontSize:10, color:'#777', letterSpacing:1.5, display:'block', marginBottom:5 }}>
            VAULT PASSPHRASE
          </label>
          <input style={{ ...INPUT, width:'100%', boxSizing:'border-box' }}
            type="password" placeholder="Vault passphrase (can differ from combat passphrase)…"
            value={passphrase} onChange={(e) => setPassphrase(e.target.value)} />
        </div>

        {/* Store secret */}
        <div>
          <label style={{ fontSize:10, color:'#777', letterSpacing:1.5, display:'block', marginBottom:5 }}>
            STORE NEW SECRET
          </label>
          <div style={{ display:'flex', gap:6 }}>
            <input style={{ ...INPUT, flex:1 }} placeholder="Key (e.g. shodan_api_key)"
              value={key} onChange={(e) => setKey(e.target.value)} />
            <input style={{ ...INPUT, flex:2 }} placeholder="Value"
              value={value} onChange={(e) => setValue(e.target.value)} />
            <button style={BTN} onClick={storeSecret} disabled={loading}>STORE</button>
          </div>
        </div>

        {/* List + reveal keys */}
        <div>
          <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:8 }}>
            <label style={{ fontSize:10, color:'#777', letterSpacing:1.5 }}>STORED KEYS</label>
            <button style={{ ...BTN, padding:'4px 10px', fontSize:10 }} onClick={listKeys} disabled={loading}>
              LIST
            </button>
          </div>
          {keys.length > 0 && (
            <div style={{ display:'flex', flexDirection:'column', gap:4 }}>
              {keys.map((k) => (
                <div key={k} style={{ display:'flex', alignItems:'center', gap:8, padding:'4px 8px', background:'#0d0408', borderRadius:5 }}>
                  <span style={{ flex:1, fontSize:12, color:'#ccc' }}>{k}</span>
                  {fetched[k] ? (
                    <span style={{ fontSize:11, color:'#888', maxWidth:200, overflow:'hidden', textOverflow:'ellipsis' }}>
                      {fetched[k]}
                    </span>
                  ) : (
                    <button
                      onClick={() => fetchSecret(k)}
                      style={{ ...BTN, padding:'3px 8px', fontSize:10, background:'#3a0f1e' }}
                    >
                      REVEAL
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
          {keys.length === 0 && (
            <div style={{ fontSize:11, color:'#333', textAlign:'center', padding:'12px 0' }}>
              Vault is empty or passphrase not entered yet.
            </div>
          )}
        </div>

        {status && (
          <div style={{ fontSize:11, color: status.startsWith('✓') ? '#4CAF50' : '#FF2D55' }}>
            {status}
          </div>
        )}
      </div>
    </motion.div>
  )
}
