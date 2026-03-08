import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useCombatStore } from '../../store/useCombatStore'

const API = (path: string) => `http://${window.location.hostname}:8000${path}`

interface CombatModeModalProps {
  open:    boolean
  onClose: () => void
}

type Step = 'AUTH_CHECK' | 'SETUP' | 'UNLOCK' | 'ACTIVATING'

export const CombatModeModal: React.FC<CombatModeModalProps> = ({ open, onClose }) => {
  const { passphraseSet, setActive, setPassphraseSet } = useCombatStore()
  const [step,        setStep]        = useState<Step>('AUTH_CHECK')
  const [passphrase,  setPassphrase]  = useState('')
  const [confirm,     setConfirm]     = useState('')
  const [agreed,      setAgreed]      = useState(false)
  const [error,       setError]       = useState('')
  const [loading,     setLoading]     = useState(false)

  // ── Check backend status when modal opens ──────────────────────────────────
  React.useEffect(() => {
    if (!open) {
      setError('')
      setPassphrase('')
      setConfirm('')
      setAgreed(false)
      return
    }
    setStep('AUTH_CHECK')
    fetch(API('/api/combat/auth/status'))
      .then((r) => r.json())
      .then((d) => {
        setPassphraseSet(d.passphrase_configured)
        setStep(d.passphrase_configured ? 'UNLOCK' : 'SETUP')
      })
      .catch(() => setStep('UNLOCK'))
  }, [open]) // eslint-disable-line react-hooks/exhaustive-deps

  // ── Setup passphrase (first run) ───────────────────────────────────────────
  const handleSetup = async () => {
    setError('')
    if (passphrase.length < 8) {
      setError('Passphrase must be at least 8 characters.')
      return
    }
    if (passphrase !== confirm) {
      setError('Passphrases do not match.')
      return
    }
    if (!agreed) {
      setError('You must acknowledge the authorisation statement.')
      return
    }
    setLoading(true)
    try {
      const r = await fetch(API('/api/combat/auth/setup'), {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ passphrase }),
      })
      if (!r.ok) {
        const d = await r.json()
        setError(d.detail || 'Setup failed.')
        return
      }
      setPassphraseSet(true)
      setStep('UNLOCK')
    } catch {
      setError('Network error.')
    } finally {
      setLoading(false)
    }
  }

  // ── Activate (unlock) ──────────────────────────────────────────────────────
  const handleActivate = async () => {
    setError('')
    if (!agreed) {
      setError('You must acknowledge the authorisation statement.')
      return
    }
    setLoading(true)
    setStep('ACTIVATING')
    try {
      const r = await fetch(API('/api/combat/auth/activate'), {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ passphrase }),
      })
      if (!r.ok) {
        const d = await r.json()
        setError(d.detail?.message || d.detail || 'Authentication failed. Check your passphrase.')
        setStep('UNLOCK')
        return
      }
      const d = await r.json()
      setActive(d.token)
      onClose()
    } catch {
      setError('Network error.')
      setStep('UNLOCK')
    } finally {
      setLoading(false)
    }
  }

  // ── Reset passphrase (forgot) ──────────────────────────────────────────────
  const handleReset = async () => {
    if (!window.confirm('This will delete the stored combat passphrase and require you to set a new one. Continue?')) return
    setLoading(true)
    try {
      await fetch(API('/api/combat/auth/reset'), { method: 'POST' })
      setPassphraseSet(false)
      setPassphrase('')
      setConfirm('')
      setError('')
      setStep('SETUP')
    } catch {
      setError('Reset failed — check backend connection.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-[9999] flex items-center justify-center"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          style={{ background: 'rgba(0,0,0,0.85)', backdropFilter: 'blur(6px)' }}
          onClick={(e) => e.target === e.currentTarget && onClose()}
        >
          <motion.div
            initial={{ scale: 0.85, opacity: 0 }}
            animate={{ scale: 1,    opacity: 1 }}
            exit={{ scale: 0.85,    opacity: 0 }}
            transition={{ type: 'spring', stiffness: 300, damping: 26 }}
            style={{
              background:   '#0F0508',
              border:       '1px solid #FF2D55',
              borderRadius: 12,
              padding:      32,
              width:        440,
              boxShadow:    '0 0 60px rgba(255,45,85,0.25)',
            }}
          >
            {/* Header */}
            <div style={{ marginBottom: 24, textAlign: 'center' }}>
              <div style={{ fontSize: 11, letterSpacing: 4, color: '#FF2D55', marginBottom: 8 }}>
                ◈ SPARK COMBAT MODE ◈
              </div>
              <div style={{ fontSize: 20, fontWeight: 700, color: '#fff' }}>
                {step === 'SETUP' ? 'First-Run Setup' : 'Authenticate'}
              </div>
              <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>
                Sovereign Cyber Intelligence Platform
              </div>
            </div>

            {/* Authorisation acknowledgement */}
            <div style={{
              background:   'rgba(255,45,85,0.08)',
              border:       '1px solid rgba(255,45,85,0.3)',
              borderRadius: 8,
              padding:      12,
              marginBottom: 20,
              fontSize:     11,
              color:        '#ff9999',
              lineHeight:   1.6,
            }}>
              ⚠ Combat Mode enables active OSINT and security research capabilities.
              By activating, you confirm that you have <strong>explicit written
              authorisation</strong> for any targets you scan, and that you accept
              full legal and ethical responsibility for all activity conducted in
              this session.
            </div>

            <label style={{ display: 'flex', alignItems: 'flex-start', gap: 10, marginBottom: 20, cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={agreed}
                onChange={(e) => setAgreed(e.target.checked)}
                style={{ marginTop: 2, accentColor: '#FF2D55' }}
              />
              <span style={{ fontSize: 12, color: '#ccc' }}>
                I have authorisation to proceed. I understand this is for
                authorised security research only.
              </span>
            </label>

            {/* Passphrase input */}
            {(step === 'SETUP' || step === 'UNLOCK' || step === 'ACTIVATING') && (
              <div style={{ marginBottom: 12 }}>
                <label style={{ fontSize: 11, color: '#777', letterSpacing: 1, display: 'block', marginBottom: 6 }}>
                  PASSPHRASE
                </label>
                <input
                  type="password"
                  value={passphrase}
                  onChange={(e) => setPassphrase(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      if (step === 'SETUP') { handleSetup(); } else { handleActivate(); }
                    }
                  }}
                  placeholder="Enter combat passphrase…"
                  autoFocus
                  style={{
                    width:        '100%',
                    background:   '#1a0810',
                    border:       '1px solid #4a1520',
                    borderRadius: 6,
                    padding:      '10px 12px',
                    color:        '#fff',
                    fontSize:     14,
                    outline:      'none',
                    boxSizing:    'border-box',
                  }}
                />
              </div>
            )}

            {/* Confirm passphrase — first run only */}
            {step === 'SETUP' && (
              <div style={{ marginBottom: 12 }}>
                <label style={{ fontSize: 11, color: '#777', letterSpacing: 1, display: 'block', marginBottom: 6 }}>
                  CONFIRM PASSPHRASE
                </label>
                <input
                  type="password"
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSetup()}
                  placeholder="Confirm passphrase…"
                  style={{
                    width:        '100%',
                    background:   '#1a0810',
                    border:       '1px solid #4a1520',
                    borderRadius: 6,
                    padding:      '10px 12px',
                    color:        '#fff',
                    fontSize:     14,
                    outline:      'none',
                    boxSizing:    'border-box',
                  }}
                />
              </div>
            )}

            {/* Error */}
            {error && (
              <div style={{ marginBottom: 16 }}>
                <div style={{ color: '#FF2D55', fontSize: 12, marginBottom: step === 'UNLOCK' ? 6 : 0 }}>
                  {error}
                </div>
                {step === 'UNLOCK' && (
                  <button
                    onClick={handleReset}
                    style={{ background: 'none', border: 'none', color: '#7a3a4a', fontSize: 11,
                      cursor: 'pointer', textDecoration: 'underline', padding: 0 }}
                  >
                    Forgot passphrase? Reset it.
                  </button>
                )}
              </div>
            )}

            {/* Action buttons */}
            <div style={{ display: 'flex', gap: 10, marginTop: 8 }}>
              <button
                onClick={onClose}
                style={{
                  flex:         1,
                  padding:      '10px 0',
                  background:   'transparent',
                  border:       '1px solid #333',
                  borderRadius: 6,
                  color:        '#888',
                  cursor:       'pointer',
                  fontSize:     13,
                }}
              >
                Cancel
              </button>
              <button
                onClick={step === 'SETUP' ? handleSetup : handleActivate}
                disabled={loading || step === 'ACTIVATING' || step === 'AUTH_CHECK'}
                style={{
                  flex:         2,
                  padding:      '10px 0',
                  background:   loading ? '#3a0f1a' : '#FF2D55',
                  border:       'none',
                  borderRadius: 6,
                  color:        '#fff',
                  cursor:       loading ? 'not-allowed' : 'pointer',
                  fontSize:     13,
                  fontWeight:   700,
                  letterSpacing: 1,
                }}
              >
                {loading     ? 'PROCESSING…'
                : step === 'SETUP'      ? 'SET PASSPHRASE'
                : step === 'ACTIVATING' ? 'ACTIVATING…'
                : 'ACTIVATE COMBAT MODE'}
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
