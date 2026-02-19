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

const rand = (min: number, max: number) => Math.random() * (max - min) + min;
const clamp = (v: number, min: number, max: number) => Math.max(min, Math.min(max, v));

function walk(current: number, min: number, max: number, step: number): number {
  return clamp(current + rand(-step, step), min, max);
}

const MAX_HISTORY = 30;

export function useSystemMetrics(): SystemMetrics {
  const startTime = useRef(Date.now());
  const [metrics, setMetrics] = useState<SystemMetrics>({
    cpu: 42, cpuHistory: [],
    ram: 58, ramHistory: [],
    gpu: 31, gpuHistory: [],
    network: 24, networkHistory: [],
    battery: 87, charging: true,
    temperature: 63,
    threatLevel: 'low',
    firewallActive: true,
    encryptionProgress: 100,
    uptime: 0,
    processes: 312,
    ping: 14,
  });

  useEffect(() => {
    const interval = setInterval(() => {
      setMetrics(prev => {
        const now = Date.now();
        const cpu = walk(prev.cpu, 5, 95, 8);
        const ram = walk(prev.ram, 20, 90, 3);
        const gpu = walk(prev.gpu, 10, 98, 10);
        const network = walk(prev.network, 0, 100, 15);
        const temperature = walk(prev.temperature, 40, 95, 2);
        const ping = Math.round(walk(prev.ping, 5, 150, 10));
        const processes = Math.round(walk(prev.processes, 200, 500, 5));
        const threatLevel: 'low' | 'medium' | 'high' =
          temperature > 80 || cpu > 85 ? 'high'
            : temperature > 70 || cpu > 70 ? 'medium'
              : 'low';

        const addPoint = (history: MetricPoint[], value: number): MetricPoint[] => {
          const updated = [...history, { value: Math.round(value), time: now }];
          return updated.slice(-MAX_HISTORY);
        };

        return {
          ...prev,
          cpu, cpuHistory: addPoint(prev.cpuHistory, cpu),
          ram, ramHistory: addPoint(prev.ramHistory, ram),
          gpu, gpuHistory: addPoint(prev.gpuHistory, gpu),
          network, networkHistory: addPoint(prev.networkHistory, network),
          temperature,
          threatLevel,
          uptime: now - startTime.current,
          processes,
          ping,
          battery: prev.charging
            ? Math.min(100, prev.battery + 0.05)
            : Math.max(0, prev.battery - 0.02),
        };
      });
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  return metrics;
}
