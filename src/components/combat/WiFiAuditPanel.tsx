/**
 * WiFiAuditPanel — Combat Mode WiFi Scanning & Handshake Capture
 * Provides: network scan, handshake capture, GPU benchmark, crack-time ETA
 */
import React, { useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useCombatStore } from '../../store/useCombatStore'

const API = (path: string) => `http://${window.location.hostname}:8000${path}`

type WifiNetwork = {
  bssid:       string
  ssid:        string
  channel:     number
  signal_dbm:  number
  encryption:  string
  clients:     number
  handshake:   boolean
}

type Benchmark = {
  hash_type:         string
  hashes_per_sec:    number
  crack_time_8char:  string
  crack_time_12char: string
}

const SIGNAL_COLOR = (dbm: number) => {
  if (dbm >= -60) return '#34d399'
  if (dbm >= -75) return '#FF9F0A'
  return '#FF2D55'
}

const ENC_COLOR = (enc: string) => {
  if (enc === 'OPEN')  return '#FF2D55'
  if (enc === 'WEP')   return '#FF9F0A'
  if (enc === 'WPA3')  return '#34d399'
  return '#60a5fa'
}

const WiFiAuditPanel: React.FC = () => {
  const { sessionToken } = useCombatStore()
  const [networks, setNetworks] = useState<WifiNetwork[]>([])
  const [scanning, setScanning] = useState(false)
  const [interface_, setInterface_] = useState('wlan0')
  const [benchmark, setBenchmark] = useState<Benchmark | null>(null)
  const [benchmarking, setBenchmarking] = useState(false)
  const [capturing, setCapturing] = useState<string | null>(null)
  const [captureResult, setCaptureResult] = useState<string | null>(null)
  const [error, setError] = useState('')

  const scan = useCallback(async () => {
    setScanning(true)
    setError('')
    try {
      const res = await fetch(API(`/api/combat/wifi/scan?interface=${encodeURIComponent(interface_)}`), {
        headers: { 'X-Combat-Token': sessionToken! },
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Scan failed')
      setNetworks(data.networks || [])
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setScanning(false)
    }
  }, [interface_, sessionToken])

  const captureHandshake = useCallback(async (net: WifiNetwork) => {
    setCapturing(net.bssid)
    setCaptureResult(null)
    try {
      const res = await fetch(API('/api/combat/wifi/capture'), {
        method:  'POST',
        headers: { 'Content-Type': 'application/json', 'X-Combat-Token': sessionToken! },
        body:    JSON.stringify({ bssid: net.bssid, channel: net.channel, interface: interface_ + 'mon', duration: 60 }),
      })
      const data = await res.json()
      setCaptureResult(data.captured ? `✓ Captured: ${data.cap_file}` : '✗ No handshake captured')
      if (data.captured) {
        setNetworks(prev => prev.map(n => n.bssid === net.bssid ? { ...n, handshake: true } : n))
      }
    } catch (e: unknown) {
      setCaptureResult(`Error: ${e instanceof Error ? e.message : String(e)}`)
    } finally {
      setCapturing(null)
    }
  }, [interface_, sessionToken])

  const runBenchmark = useCallback(async () => {
    setBenchmarking(true)
    try {
      const res = await fetch(API('/api/combat/wifi/benchmark'), {
        headers: { 'X-Combat-Token': sessionToken! },
      })
      const data = await res.json()
      setBenchmark(data)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBenchmarking(false)
    }
  }, [sessionToken])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12, height: '100%' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <span style={{ color: '#FF2D55', fontSize: 11, fontWeight: 700, letterSpacing: 2 }}>
          WIFI AUDIT
        </span>
        <input
          value={interface_}
          onChange={e => setInterface_(e.target.value)}
          placeholder="interface (wlan0)"
          style={{
            background: '#19050c', border: '1px solid #3a1520', borderRadius: 4,
            padding: '4px 8px', color: '#fff', fontSize: 11, width: 120,
          }}
        />
        <button
          onClick={scan}
          disabled={scanning}
          style={{
            background: scanning ? '#3a1520' : '#FF2D55', border: 'none',
            borderRadius: 4, padding: '4px 14px', color: '#fff',
            fontSize: 11, fontWeight: 700, cursor: 'pointer',
          }}
        >
          {scanning ? 'SCANNING…' : 'SCAN'}
        </button>
        <button
          onClick={runBenchmark}
          disabled={benchmarking}
          style={{
            background: 'transparent', border: '1px solid #3a1520',
            borderRadius: 4, padding: '4px 12px', color: '#888',
            fontSize: 11, cursor: 'pointer',
          }}
        >
          {benchmarking ? 'BENCHMARKING…' : 'GPU BENCH'}
        </button>
      </div>

      {error && (
        <div style={{ color: '#FF2D55', fontSize: 11, padding: '6px 10px',
          background: '#1a0005', borderRadius: 4, border: '1px solid #3a1520' }}>
          {error}
        </div>
      )}

      {/* Benchmark */}
      <AnimatePresence>
        {benchmark && (
          <motion.div
            initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            style={{ background: '#0d0003', border: '1px solid #3a1520', borderRadius: 6, padding: '8px 12px' }}
          >
            <div style={{ color: '#888', fontSize: 10, letterSpacing: 1, marginBottom: 4 }}>GPU BENCHMARK</div>
            <div style={{ display: 'flex', gap: 24 }}>
              <span style={{ color: '#34d399', fontSize: 12, fontWeight: 700 }}>
                {(benchmark.hashes_per_sec / 1e6).toFixed(2)} MH/s
              </span>
              <span style={{ color: '#888', fontSize: 11 }}>8-char: {benchmark.crack_time_8char}</span>
              <span style={{ color: '#888', fontSize: 11 }}>12-char: {benchmark.crack_time_12char}</span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Capture result */}
      <AnimatePresence>
        {captureResult && (
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            style={{
              color: captureResult.startsWith('✓') ? '#34d399' : '#FF2D55',
              fontSize: 11, padding: '4px 10px', background: '#0d0003',
              borderRadius: 4, border: '1px solid #3a1520',
            }}
          >
            {captureResult}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Network table */}
      {networks.length > 0 ? (
        <div style={{ flex: 1, overflowY: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #2a0010' }}>
                {['SSID', 'BSSID', 'CH', 'SIGNAL', 'ENC', 'CLIENTS', 'ACTION'].map(h => (
                  <th key={h} style={{ color: '#555', fontWeight: 600, letterSpacing: 1,
                    padding: '4px 8px', textAlign: 'left' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {networks.map(net => (
                <tr key={net.bssid} style={{ borderBottom: '1px solid #19050c' }}>
                  <td style={{ color: '#fff', padding: '5px 8px' }}>
                    {net.ssid}
                    {net.handshake && <span style={{ color: '#34d399', marginLeft: 6, fontSize: 10 }}>●HS</span>}
                  </td>
                  <td style={{ color: '#555', padding: '5px 8px', fontFamily: 'monospace' }}>{net.bssid}</td>
                  <td style={{ color: '#888', padding: '5px 8px' }}>{net.channel}</td>
                  <td style={{ padding: '5px 8px' }}>
                    <span style={{ color: SIGNAL_COLOR(net.signal_dbm), fontWeight: 700 }}>
                      {net.signal_dbm} dBm
                    </span>
                  </td>
                  <td style={{ padding: '5px 8px' }}>
                    <span style={{ color: ENC_COLOR(net.encryption), fontWeight: 700, fontSize: 10 }}>
                      {net.encryption}
                    </span>
                  </td>
                  <td style={{ color: '#888', padding: '5px 8px', textAlign: 'center' }}>{net.clients}</td>
                  <td style={{ padding: '5px 8px' }}>
                    {net.encryption !== 'OPEN' && net.encryption !== 'WPA3' && (
                      <button
                        onClick={() => captureHandshake(net)}
                        disabled={capturing === net.bssid}
                        style={{
                          background: 'transparent', border: '1px solid #FF2D55',
                          borderRadius: 4, padding: '2px 8px', color: '#FF2D55',
                          fontSize: 10, cursor: 'pointer', fontWeight: 700,
                        }}
                      >
                        {capturing === net.bssid ? 'CAPTURING…' : 'CAPTURE'}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <span style={{ color: '#2a0010', fontSize: 12 }}>
            {scanning ? 'Scanning for networks…' : 'Run SCAN to enumerate nearby networks'}
          </span>
        </div>
      )}
    </div>
  )
}

export default WiFiAuditPanel
