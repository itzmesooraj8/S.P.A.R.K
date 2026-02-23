import { useState, useEffect, useRef } from 'react';

export interface MetricPoint { value: number; time: number; }
export interface SystemMetrics {
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
  ping: number;
}



const MAX_HISTORY = 30;

export function useSystemMetrics(): SystemMetrics {
  const startTime = useRef(Date.now());

  // Default fallback values mapped to our interface
  const [metrics, setMetrics] = useState<SystemMetrics>({
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

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          if (data.type === "STATE_UPDATE" && data.state && data.state.metrics) {
            const metricsPayload = data.state.metrics;
            const now = Date.now();

            setMetrics(prev => {
              // Process CPU
              const cpuValue = metricsPayload.cpu ?? prev.cpu;
              const newCpuHistory = [...prev.cpuHistory, { value: Math.round(cpuValue), time: now }].slice(-MAX_HISTORY);

              // Process RAM
              const ramValue = metricsPayload.ram ?? prev.ram;
              const newRamHistory = [...prev.ramHistory, { value: Math.round(ramValue), time: now }].slice(-MAX_HISTORY);

              // Process GPU
              const gpuValue = metricsPayload.gpu ?? prev.gpu;
              const newGpuHistory = [...prev.gpuHistory, { value: Math.round(gpuValue), time: now }].slice(-MAX_HISTORY);

              // Process Network
              const networkValue = metricsPayload.network ?? prev.network;
              const newNetworkHistory = [...prev.networkHistory, { value: Math.round(networkValue), time: now }].slice(-MAX_HISTORY);

              // Threat Level heuristic
              const threatLevel: 'low' | 'medium' | 'high' = cpuValue > 85 ? 'high' : cpuValue > 70 ? 'medium' : 'low';

              return {
                ...prev,
                cpu: cpuValue,
                cpuHistory: newCpuHistory,
                ram: ramValue,
                ramHistory: newRamHistory,
                gpu: gpuValue,
                gpuHistory: newGpuHistory,
                network: networkValue,
                networkHistory: newNetworkHistory,
                battery: metricsPayload.battery ?? prev.battery,
                charging: metricsPayload.charging ?? prev.charging,
                threatLevel: threatLevel,
                uptime: now - startTime.current,
              };
            });
          }
        } catch (error) {
          console.error("[useSystemMetrics] Failed to parse payload:", error);
        }
      };

      ws.onclose = () => {
        console.warn("[useSystemMetrics] Disconnected. Reconnecting in 2s...");
        reconnectTimeout = setTimeout(connect, 2000);
      };

      ws.onerror = (error) => {
        console.error("[useSystemMetrics] WebSocket Error:", error);
        ws.close();
      };
    };

    connect();

    return () => {
      clearTimeout(reconnectTimeout);
      if (ws) {
        ws.close();
      }
    };
  }, []);

  return metrics;
}
