import { create } from 'zustand'
import { persist, subscribeWithSelector } from 'zustand/middleware'

// ── Types ─────────────────────────────────────────────────────────────────────

export type CombatHudLevel = 'PASSIVE' | 'ACTIVE' | 'COMBAT'

export interface VpnStatus {
  vpn_detected:   boolean
  tor_detected:   boolean
  public_ip:      string
  vpn_interfaces: string[]
  exposed:        boolean
  warning:        string
}

export interface ScopeTarget {
  target: string
}

export interface HuntHit {
  platform: string
  url:      string
  found:    boolean
  job_id:   string
  username: string
}

export type CombatPanel = 'identity' | 'sigint' | 'tor' | 'vault' | 'recon' | 'wifi' | 'password' | null

// ── State interface ────────────────────────────────────────────────────────────

interface CombatState {
  // Mode
  isActive:        boolean
  hudLevel:        CombatHudLevel
  sessionToken:    string | null
  passphraseSet:   boolean

  // OpSec
  vpnStatus:       VpnStatus | null
  vpnChecked:      boolean

  // Scope
  scopeTargets:    string[]

  // Active panel
  activePanel:     CombatPanel

  // Identity hunt results
  huntResults:     HuntHit[]
  huntJobId:       string | null
  huntInProgress:  boolean

  // Sigint
  sigintFeeds:     Record<string, unknown> | null
  sigintLoading:   boolean

  // Recon
  passiveResults:  Record<string, unknown> | null
  activeResults:   Record<string, unknown> | null
  reconLoading:    boolean

  // Actions
  setActive:        (token: string) => void
  setInactive:      () => void
  setHudLevel:      (level: CombatHudLevel) => void
  setPassphraseSet: (v: boolean) => void
  setVpnStatus:     (s: VpnStatus) => void
  setActivePanel:   (p: CombatPanel) => void
  addHuntHit:       (hit: HuntHit) => void
  clearHuntResults: () => void
  setHuntJobId:     (id: string | null) => void
  setHuntInProgress:(v: boolean) => void
  setScopeTargets:  (targets: string[]) => void
  setSigintFeeds:   (feeds: Record<string, unknown>) => void
  setSigintLoading: (v: boolean) => void
  setPassiveResults:(r: Record<string, unknown> | null) => void
  setActiveResults: (r: Record<string, unknown> | null) => void
  setReconLoading:  (v: boolean) => void
}

// ── Store ─────────────────────────────────────────────────────────────────────

export const useCombatStore = create<CombatState>()(
  subscribeWithSelector(
    persist(
      (set) => ({
        // Initial state
        isActive:        false,
        hudLevel:        'PASSIVE',
        sessionToken:    null,
        passphraseSet:   false,

        vpnStatus:       null,
        vpnChecked:      false,

        scopeTargets:    [],
        activePanel:     null,

        huntResults:     [],
        huntJobId:       null,
        huntInProgress:  false,

        sigintFeeds:     null,
        sigintLoading:   false,

        passiveResults:  null,
        activeResults:   null,
        reconLoading:    false,

        // Actions
        setActive: (token) =>
          set({ isActive: true, hudLevel: 'COMBAT', sessionToken: token }),

        setInactive: () =>
          set({
            isActive:       false,
            hudLevel:       'PASSIVE',
            sessionToken:   null,
            activePanel:    null,
            vpnChecked:     false,
          }),

        setHudLevel:       (hudLevel) => set({ hudLevel }),
        setPassphraseSet:  (passphraseSet) => set({ passphraseSet }),
        setVpnStatus:      (vpnStatus) => set({ vpnStatus, vpnChecked: true }),
        setActivePanel:    (activePanel) => set({ activePanel }),

        addHuntHit: (hit) =>
          set((s) => ({ huntResults: [...s.huntResults, hit] })),

        clearHuntResults: () =>
          set({ huntResults: [], huntJobId: null, huntInProgress: false }),

        setHuntJobId:      (huntJobId) => set({ huntJobId }),
        setHuntInProgress: (huntInProgress) => set({ huntInProgress }),

        setScopeTargets:  (scopeTargets) => set({ scopeTargets }),
        setSigintFeeds:   (sigintFeeds) => set({ sigintFeeds }),
        setSigintLoading: (sigintLoading) => set({ sigintLoading }),
        setPassiveResults:(passiveResults) => set({ passiveResults }),
        setActiveResults: (activeResults) => set({ activeResults }),
        setReconLoading:  (reconLoading) => set({ reconLoading }),
      }),
      {
        name: 'spark-combat-store',
        // Don't persist sensitive state
        partialize: (state) => ({
          passphraseSet: state.passphraseSet,
          scopeTargets:  state.scopeTargets,
        }),
      }
    )
  )
)

// ── Derived selectors ─────────────────────────────────────────────────────────

export const selectCombatToken  = (s: CombatState) => s.sessionToken
export const selectIsExposed    = (s: CombatState) => s.vpnStatus?.exposed ?? false
export const selectHudLevel     = (s: CombatState) => s.hudLevel

// Combat palette helper
export const COMBAT_BG          = '#0F0508'
export const COMBAT_ACCENT      = '#FF2D55'
export const COMBAT_ACCENT_DIM  = '#7D1627'
export const PASSIVE_BG         = '#010812'
