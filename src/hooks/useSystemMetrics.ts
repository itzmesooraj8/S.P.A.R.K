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

          if (data.type === "METRICS") {
            const now = Date.now();

            setMetrics(prev => {
              // 1. Process CPU
              const cpuValue = data.cpu ?? prev.cpu;
              const newCpuHistory = [...prev.cpuHistory, { value: Math.round(cpuValue), time: now }].slice(-MAX_HISTORY);

              // 2. Process RAM
              const ramValue = data.ram ?? prev.ram;
              const newRamHistory = [...prev.ramHistory, { value: Math.round(ramValue), time: now }].slice(-MAX_HISTORY);

              // 3. Optional map Disk -> Network/GPU temporary if needed
              const diskValue = data.disk ?? prev.gpu;
              const newGpuHistory = [...prev.gpuHistory, { value: Math.round(diskValue), time: now }].slice(-MAX_HISTORY);

              // 4. Calculate Threat Level based on real incoming CPU
              const threatLevel: 'low' | 'medium' | 'high' = cpuValue > 85 ? 'high' : cpuValue > 70 ? 'medium' : 'low';

              return {
                ...prev,
                cpu: cpuValue,
                cpuHistory: newCpuHistory,
                ram: ramValue,
                ramHistory: newRamHistory,
                gpu: diskValue, // Mapping disk to gpu for now
                gpuHistory: newGpuHistory,
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
