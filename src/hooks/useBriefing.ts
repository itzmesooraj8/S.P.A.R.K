/**
 * useBriefing — Jarvis proactive briefing hook
 * Fetches and caches a Jarvis briefing, re-fetching on combat activation.
 */
import { useState, useEffect, useCallback } from 'react'
import { useCombatStore } from '@/store/useCombatStore'

type BriefingData = {
  text:      string
  audio_url: string
  timestamp: string
  mode:      string
}

export function useBriefing(autoSpeak = false) {
  const { isActive, sessionToken } = useCombatStore()
  const [briefing, setBriefing]   = useState<BriefingData | null>(null)
  const [loading, setLoading]     = useState(false)
  const [error, setError]         = useState<string | null>(null)

  const fetch_ = useCallback(async (mode = 'PASSIVE') => {
    if (!sessionToken) return
    setLoading(true); setError(null)
    try {
      const res = await fetch(
        `${window.location.protocol}//${window.location.hostname}:8000/api/combat/jarvis/briefing`,
        {
          method:  'POST',
          headers: { 'Content-Type': 'application/json', 'X-Combat-Token': sessionToken },
          body:    JSON.stringify({
            mode,
            speak:   autoSpeak,
            context: { combat_active: isActive },
          }),
        },
      )
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data: BriefingData = await res.json()
      setBriefing(data)

      // If we have audio and autoSpeak is set, play it
      if (autoSpeak && data.audio_url) {
        try {
          const audio = new Audio(data.audio_url)
          await audio.play()
        } catch { /* user interaction required or audio disabled */ }
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }, [sessionToken, isActive, autoSpeak])

  useEffect(() => {
    if (isActive) {
      fetch_('COMBAT')
    } else {
      setBriefing(null)
    }
  }, [isActive, fetch_])

  return { briefing, loading, error, refetch: fetch_ }
}
