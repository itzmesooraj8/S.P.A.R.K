import { useEffect, useRef, useCallback } from 'react'
import { useCombatStore } from '../store/useCombatStore'

const WS_URL = () => `ws://${window.location.hostname}:8000/ws/combat`

// Reconnect delays: 1s, 2s, 4s, 8s, 16s, 30s (capped)
const RECONNECT_DELAYS = [1000, 2000, 4000, 8000, 16000, 30000]

/**
 * useCombatWS
 * -----------
 * Opens a WebSocket to /ws/combat when combat mode is active.
 * • Dispatches all messages to the Zustand store (HUNT_HIT, HUNT_STARTED, etc.)
 * • Broadcasts every message as a `spark:ws` CustomEvent so any component
 *   (SentinelModule sensor tab, PasswordAuditPanel, WiFiAuditPanel, etc.)
 *   can subscribe without prop-drilling.
 * • Auto-reconnects with exponential back-off on disconnect.
 */
export function useCombatWS(): void {
  const isActive          = useCombatStore((s) => s.isActive)
  const addHuntHit        = useCombatStore((s) => s.addHuntHit)
  const setHuntInProgress = useCombatStore((s) => s.setHuntInProgress)

  const wsRef       = useRef<WebSocket | null>(null)
  const retryRef    = useRef<ReturnType<typeof setTimeout> | null>(null)
  const retryCount  = useRef(0)
  const destroyed   = useRef(false)   // set on cleanup to stop reconnect loop

  const clearRetry = () => {
    if (retryRef.current) { clearTimeout(retryRef.current); retryRef.current = null }
  }

  const handleMessage = useCallback((msg: Record<string, unknown>) => {
    // 1. Broadcast to all listeners as a custom event (real-time panel updates)
    window.dispatchEvent(new CustomEvent('spark:ws', { detail: msg }))

    // 2. Apply to Zustand store for combat-global state
    const type = msg.type as string | undefined
    switch (type) {
      case 'HUNT_HIT':
        addHuntHit({
          job_id:   msg.job_id   as string,
          username: msg.username as string,
          platform: msg.platform as string,
          url:      msg.url      as string,
          found:    Boolean(msg.found),
        })
        break
      case 'HUNT_STARTED':
        setHuntInProgress(true)
        break
      case 'HUNT_COMPLETE':
      case 'HUNT_ERROR':
        setHuntInProgress(false)
        break
      default:
        break
    }
  }, [addHuntHit, setHuntInProgress])

  const connect = useCallback(() => {
    if (destroyed.current) return

    const ws = new WebSocket(WS_URL())
    wsRef.current = ws

    ws.onopen = () => {
      console.log('[CombatWS] Connected')
      retryCount.current = 0
    }

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data as string)
        handleMessage(msg)
      } catch { /* non-JSON frame — ignore */ }
    }

    ws.onerror = (e) => console.error('[CombatWS] Error', e)

    ws.onclose = () => {
      wsRef.current = null
      if (destroyed.current) return
      // Exponential back-off reconnect
      const delay = RECONNECT_DELAYS[Math.min(retryCount.current, RECONNECT_DELAYS.length - 1)]
      retryCount.current += 1
      console.log(`[CombatWS] Reconnecting in ${delay}ms (attempt ${retryCount.current})…`)
      retryRef.current = setTimeout(connect, delay)
    }
  }, [handleMessage])

  useEffect(() => {
    if (!isActive) {
      destroyed.current = true
      clearRetry()
      wsRef.current?.close()
      wsRef.current = null
      return
    }

    destroyed.current = false
    retryCount.current = 0
    connect()

    return () => {
      destroyed.current = true
      clearRetry()
      wsRef.current?.close()
      wsRef.current = null
    }
  }, [isActive, connect])
}
