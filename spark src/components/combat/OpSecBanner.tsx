import React, { useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useCombatStore } from '../../store/useCombatStore'

const API = (path: string) => `http://${window.location.hostname}:8000${path}`

/**
 * OpSec banner that appears at the top of the Combat HUD when
 * no VPN/Tor is detected (i.e. the operator's real IP is exposed).
 */
export const OpSecBanner: React.FC = () => {
  const { isActive, vpnStatus, vpnChecked, sessionToken, setVpnStatus } = useCombatStore()

  // Run VPN check whenever combat mode activates
  useEffect(() => {
    if (!isActive || !sessionToken || vpnChecked) return

    fetch(API('/api/combat/opsec/check'), {
      headers: { 'X-Combat-Token': sessionToken },
    })
      .then((r) => r.json())
      .then((d) => setVpnStatus(d))
      .catch(() => {/* non-critical */})
  }, [isActive, sessionToken, vpnChecked]) // eslint-disable-line react-hooks/exhaustive-deps

  const show = isActive && vpnChecked && (vpnStatus?.exposed ?? false)

  return (
    <AnimatePresence>
      {show && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          transition={{ duration: 0.3 }}
          style={{
            background:   'linear-gradient(90deg, #3a0f0f 0%, #2a0808 100%)',
            borderBottom: '1px solid #FF2D55',
            overflow:     'hidden',
          }}
        >
          <div style={{
            display:    'flex',
            alignItems: 'center',
            gap:        12,
            padding:    '8px 20px',
          }}>
            {/* Pulsing warning dot */}
            <motion.div
              animate={{ opacity: [1, 0.3, 1] }}
              transition={{ duration: 1.2, repeat: Infinity }}
              style={{
                width:        8,
                height:       8,
                borderRadius: '50%',
                background:   '#FF2D55',
                flexShrink:   0,
              }}
            />

            <div style={{ flex: 1 }}>
              <span style={{ color: '#FF2D55', fontWeight: 700, fontSize: 11, letterSpacing: 2 }}>
                OPSEC ALERT
              </span>
              <span style={{ color: '#ff9999', fontSize: 11, marginLeft: 12 }}>
                {vpnStatus?.warning || 'No VPN or Tor circuit detected. Your real IP may be exposed.'}
              </span>
              {vpnStatus?.public_ip && vpnStatus.public_ip !== 'unknown' && (
                <span style={{ color: '#ff6680', fontSize: 11, marginLeft: 8 }}>
                  Public IP: <strong>{vpnStatus.public_ip}</strong>
                </span>
              )}
            </div>

            <div style={{ fontSize: 10, color: '#664', cursor: 'default' }}>
              AUTHORISED RESEARCH ONLY
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
