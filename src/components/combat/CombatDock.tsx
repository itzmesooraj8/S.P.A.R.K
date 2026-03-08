import React from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useCombatStore, CombatPanel } from '../../store/useCombatStore'

interface DockButtonProps {
  label:    string
  icon:     string
  panel:    CombatPanel
  active:   boolean
  onClick:  () => void
}

const DockButton: React.FC<DockButtonProps> = ({ label, icon, active, onClick }) => (
  <motion.button
    whileHover={{ scale: 1.05, boxShadow: '0 0 16px rgba(255,45,85,0.4)' }}
    whileTap={{ scale: 0.95 }}
    onClick={onClick}
    style={{
      display:        'flex',
      flexDirection:  'column',
      alignItems:     'center',
      justifyContent: 'center',
      gap:            4,
      padding:        '8px 14px',
      background:     active ? 'rgba(255,45,85,0.18)' : 'rgba(15,5,8,0.9)',
      border:         `1px solid ${active ? '#FF2D55' : '#3a0f1e'}`,
      borderRadius:   8,
      cursor:         'pointer',
      color:          active ? '#FF2D55' : '#7a3a4a',
      transition:     'all 0.2s',
      minWidth:       60,
    }}
  >
    <span style={{ fontSize: 16 }}>{icon}</span>
    <span style={{ fontSize: 9, letterSpacing: 1.5, fontWeight: 700 }}>{label}</span>
  </motion.button>
)

interface CombatDockProps {
  /** Called when user wants to open the activation modal */
  onOpenModal: () => void
}

export const CombatDock: React.FC<CombatDockProps> = ({ onOpenModal }) => {
  const { isActive, activePanel, setActivePanel, setInactive, sessionToken } = useCombatStore()

  const toggle = (panel: CombatPanel) => {
    setActivePanel(activePanel === panel ? null : panel)
  }

  const deactivate = async () => {
    if (!sessionToken) { setInactive(); return }
    try {
      await fetch(`http://${window.location.hostname}:8000/api/combat/auth/deactivate`, {
        method:  'POST',
        headers: { 'X-Combat-Token': sessionToken },
      })
    } catch { /* best-effort */ }
    setInactive()
  }

  return (
    <div style={{
      display:      'flex',
      alignItems:   'center',
      gap:           6,
      padding:      '0 8px',
    }}>
      {/* Separator from standard dock buttons */}
      <div style={{ width: 1, height: 28, background: '#FF2D55', opacity: 0.4, marginRight: 4 }} />

      {!isActive ? (
        /* Combat mode entry button */
        <motion.button
          whileHover={{ scale: 1.05, boxShadow: '0 0 20px rgba(255,45,85,0.5)' }}
          whileTap={{ scale: 0.95 }}
          onClick={onOpenModal}
          style={{
            display:        'flex',
            alignItems:     'center',
            gap:             6,
            padding:        '6px 14px',
            background:     'rgba(15,5,8,0.9)',
            border:         '1px solid #3a0f1e',
            borderRadius:    8,
            cursor:         'pointer',
            color:          '#7a3a4a',
          }}
        >
          <span style={{ fontSize: 14 }}>⚔</span>
          <span style={{ fontSize: 10, letterSpacing: 2, fontWeight: 700 }}>COMBAT</span>
        </motion.button>
      ) : (
        <>
          {/* Active combat dock buttons */}
          <DockButton label="RECON"  icon="🔍" panel="identity" active={activePanel === 'identity' || activePanel === 'recon'} onClick={() => toggle('identity')} />
          <DockButton label="SIGINT" icon="📡" panel="sigint"   active={activePanel === 'sigint'}   onClick={() => toggle('sigint')}   />
          <DockButton label="TOR"    icon="🧅" panel="tor"      active={activePanel === 'tor'}       onClick={() => toggle('tor')}      />
          <DockButton label="VAULT"  icon="🔐" panel="vault"    active={activePanel === 'vault'}     onClick={() => toggle('vault')}    />
          <DockButton label="WIFI"   icon="📶" panel="wifi"     active={activePanel === 'wifi'}      onClick={() => toggle('wifi')}     />
          <DockButton label="PASSWD" icon="🔑" panel="password" active={activePanel === 'password'}  onClick={() => toggle('password')} />

          {/* Deactivate button */}
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={deactivate}
            style={{
              display:     'flex',
              alignItems:  'center',
              gap:          4,
              padding:     '6px 10px',
              background:  'rgba(255,45,85,0.12)',
              border:      '1px solid #FF2D55',
              borderRadius: 8,
              cursor:      'pointer',
              color:       '#FF2D55',
              fontSize:    9,
              fontWeight:  700,
              letterSpacing: 1,
            }}
          >
            <span style={{ fontSize: 12 }}>✕</span>
            <span>EXIT</span>
          </motion.button>
        </>
      )}
    </div>
  )
}
