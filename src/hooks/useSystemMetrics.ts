import { useState, useEffect, useRef } from 'react';
import { SystemWsMessage, SystemMetrics as ContractMetrics } from '../types/contracts';

const MAX_HISTORY = 30;

export interface MetricPoint { value: number; time: number; }

export interface LegacySystemMetrics {
  cpu: number; cpuHistory: MetricPoint[];
  ram: number; ramHistory: MetricPoint[];
  gpu: number; gpuHistory: MetricPoint[];
  network: number; networkHistory: MetricPoint[];
  battery: number; charging: boolean;
  temperature: number;
  threatLevel: 'low' | 'medium' | 'high';
  firewallActive: boolean;
  encryptionProgress: number;
  uptime: number;
  processes: number;
  ping: number;  // new
  auditMeta?: any;}

export function useSystemMetrics(): LegacySystemMetrics & { isOnline: boolean } {
  const startTime = useRef(Date.now());
  const [isOnline, setIsOnline] = useState(false);

  // Default fallback values mapped to our interface
  const [metrics, setMetrics] = useState<LegacySystemMetrics>({
    cpu: 0, cpuHistory: [],
    ram: 0, ramHistory: [],
    gpu: 0, gpuHistory: [],
    network: 0, networkHistory: [],
    battery: 100, charging: true,
    temperature: 45,
    threatLevel: 'low',
    firewallActive: true,
    encryptionProgress: 100,
    uptime: 0,
    processes: 0,
    ping: 0,
  });

  useEffect(() => {
    let ws: WebSocket;
    let reconnectTimeout: NodeJS.Timeout;

    const connect = () => {
      // Connect to Sovereign Core backend
      ws = new WebSocket("ws://localhost:8000/ws/system");

      ws.onopen = () => {
          setIsOnline(true);
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data); 

          if (msg.type === "STATE_UPDATE" && msg.state && msg.state.metrics) {
            const metricsPayload = msg.state.metrics; // This is the payload from backend, might not match ContractMetrics exactly yet if backend isn't updated, but user asked to use contracts in hook. 
            // Assuming backend sends keys compatible with what we expect or we map them.
            // Actually, backend sends "cpu", "ram", "gpu", "network" (from monitor.py).
            // Contracts say "cpu_percent".
            // I will support both for robustness or assume backend will be updated to match contract.
            // The plan says "Update Frontend Hooks ... to use contracts". 
            // It also says "Fix Backend ...". 
            
            // Let's assume the payload comes in as the Contract defined structure or map it.
            // Monitor.py sends "cpu", "ram".
            // I should update monitor.py too? "Fix Backend Tool Handler" is the only backend task mentioned besides "Implement GET /api/tools".
            // It doesn't say "Update SystemMonitor to match contracts".
            // But "Align Frontend and Backend" is the goal.
            
            // I will handle mapping here.
            
            const cpu = metricsPayload.cpu_percent ?? metricsPayload.cpu ?? 0;
            const ram = metricsPayload.memory_percent ?? metricsPayload.ram ?? 0;
            const gpu = metricsPayload.gpu_stats?.load ?? metricsPayload.gpu ?? 0;
            const network = metricsPayload.net_io ? (metricsPayload.net_io.bytes_recv + metricsPayload.net_io.bytes_sent) / 1024 : (metricsPayload.network ?? 0); // simplistic

            const now = Date.now();

            setMetrics(prev => ({
                ...prev,
                cpu: cpu,
                cpuHistory: [...prev.cpuHistory, { value: cpu, time: now }].slice(-MAX_HISTORY),
                ram: ram,
                ramHistory: [...prev.ramHistory, { value: ram, time: now }].slice(-MAX_HISTORY),
                gpu: gpu,
                gpuHistory: [...prev.gpuHistory, { value: gpu, time: now }].slice(-MAX_HISTORY),
                network: network,
                networkHistory: [...prev.networkHistory, { value: network, time: now }].slice(-MAX_HISTORY),
                uptime: now - startTime.current,
                threatLevel: cpu > 80 ? 'high' : 'low', // simple heuristic
                auditMeta: metricsPayload.audit_meta || prev.auditMeta
            }));

          } else if (msg.type === "AUDIT_UPDATE") {
              // Handle audit update - for now just log or maybe update threat level
              console.log("Audit update:", msg);
          }
        } catch (error) {
          console.error("[useSystemMetrics] Failed to parse payload:", error);
        }
      };

      ws.onclose = () => {
        setIsOnline(false);
        console.warn("[useSystemMetrics] Disconnected. Reconnecting in 2s...");
        reconnectTimeout = setTimeout(connect, 2000);
      };

      ws.onerror = (error) => {
        setIsOnline(false);
        console.error("[useSystemMetrics] WebSocket Error:", error);
        ws.close();
      };
    };

    connect();

    return () => {
      clearTimeout(reconnectTimeout);
      if (ws) ws.close();
    };
  }, []);

  return { ...metrics, isOnline };
}
