import { useState, useEffect, useRef, useCallback } from 'react';
import { SystemWsMessage, SystemMetrics as ContractMetrics } from '../types/contracts';
import { useAlertStore } from '@/store/useAlertStore';
import { useAgentConfirmStore } from '@/store/useAgentConfirmStore';
import { useActionFeedStore } from '@/store/useActionFeedStore';
import { useConnectionStore } from '@/store/useConnectionStore';

// Only log WS noise when explicitly opted-in (prevents console spam when backend is offline)
const VERBOSE_WS = import.meta.env.VITE_VERBOSE_WS === 'true';
const wsLog  = (...a: unknown[]) => VERBOSE_WS && console.log('[System WS]',  ...a);
const wsWarn = (...a: unknown[]) => VERBOSE_WS && console.warn('[System WS]', ...a);
const wsErr  = (...a: unknown[]) => VERBOSE_WS && console.error('[System WS]', ...a);

const MAX_HISTORY = 30;

const WS_URL = (() => {
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
  const port  = import.meta.env.VITE_BACKEND_PORT ?? '8000';
  return `${proto}://${window.location.hostname}:${port}/ws/system`;
})();

const RECONNECT_BASE_MS  = 2_000;
const RECONNECT_MAX_MS   = 30_000;
const PING_INTERVAL_MS   = 20_000;

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
  ping: number;
  auditMeta?: unknown;
}

export function useSystemMetrics(): LegacySystemMetrics & { isOnline: boolean } {
  const startTime  = useRef(Date.now());
  const ws         = useRef<WebSocket | null>(null);
  const retryDelay = useRef(RECONNECT_BASE_MS);
  const pingTimer  = useRef<ReturnType<typeof setInterval> | null>(null);
  const mountedRef = useRef(true);

  const [isOnline, setIsOnline] = useState(false);

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

  const stopPing = useCallback(() => {
    if (pingTimer.current) { clearInterval(pingTimer.current); pingTimer.current = null; }
  }, []);

  const connect = useCallback(() => {
    if (!mountedRef.current) return;
    if (ws.current && ws.current.readyState <= WebSocket.OPEN) return;

    const socket = new WebSocket(WS_URL);
    ws.current = socket;

    socket.onopen = () => {
      if (!mountedRef.current) { socket.close(); return; }
      setIsOnline(true);
      useConnectionStore.getState().setCoreOnline(true);
      retryDelay.current = RECONNECT_BASE_MS;
      wsLog('connected');

      // Keep-alive heartbeat
      stopPing();
      pingTimer.current = setInterval(() => {
        if (socket.readyState === WebSocket.OPEN) {
          socket.send(JSON.stringify({ v: 1, type: 'PING', ts: Date.now() }));
        }
      }, PING_INTERVAL_MS);
    };

    socket.onmessage = (event: MessageEvent) => {
      try {
        const msg = JSON.parse(event.data as string);

        // Ignore keep-alive replies
        if (msg.type === 'PONG') return;

        // ── ALERT frames → global alert store ───────────────────────────────
        if (msg.type === 'ALERT') {
          useAlertStore.getState().addAlert({
            severity: msg.severity ?? 'info',
            title:    msg.title   ?? 'System Alert',
            body:     msg.body    ?? msg.message ?? '',
            source:   msg.source  ?? 'spark-core',
            ts:       msg.ts      ?? Date.now(),
          });
          return;
        }

        // ── CONFIRM_TOOL frames → agent confirm store ────────────────────────
        if (msg.type === 'CONFIRM_TOOL') {
          useAgentConfirmStore.getState().setPending({
            token:       msg.token,
            tool:        msg.tool,
            command:     msg.command,
            risk_level:  msg.risk_level ?? 'HIGH',
            description: msg.description,
            arguments:   msg.arguments,
          });
          return;
        }

        // ── PLAN frames → action feed store ─────────────────────────────────
        if (msg.type === 'PLAN') {
          useActionFeedStore.getState().addPlan({
            plan_id: msg.plan_id,
            intent:  msg.intent   ?? 'CHAT',
            query:   msg.query    ?? '',
            steps:   msg.steps    ?? [],
            ts:      msg.ts       ?? Date.now(),
          });
          return;
        }

        // ── STEP frames → action feed store (update step status) ────────────
        if (msg.type === 'STEP') {
          useActionFeedStore.getState().updateStep(msg.plan_id, msg.step_idx, {
            status: msg.status,
            result: msg.result ?? null,
            ts:     msg.ts    ?? Date.now(),
          });
          return;
        }
        if (msg.type === 'STATE_UPDATE' && msg.state?.metrics) {
          const p: ContractMetrics & Record<string, unknown> = msg.state.metrics;

          const cpu     = (p.cpu_percent  ?? (p as Record<string, unknown>).cpu  ?? 0) as number;
          const ram     = (p.memory_percent ?? (p as Record<string, unknown>).ram ?? 0) as number;
          const gpu     = p.gpu_stats?.load ?? ((p as Record<string, unknown>).gpu as number ?? 0);
          const netObj  = p.net_io;
          const network = netObj
            ? (netObj.bytes_recv + netObj.bytes_sent) / 1024
            : ((p as Record<string, unknown>).network as number ?? 0);
          const now = Date.now();

          setMetrics(prev => ({
            ...prev,
            cpu,
            cpuHistory:  [...prev.cpuHistory,  { value: cpu,     time: now }].slice(-MAX_HISTORY),
            ram,
            ramHistory:  [...prev.ramHistory,  { value: ram,     time: now }].slice(-MAX_HISTORY),
            gpu,
            gpuHistory:  [...prev.gpuHistory,  { value: gpu,     time: now }].slice(-MAX_HISTORY),
            network,
            networkHistory: [...prev.networkHistory, { value: network, time: now }].slice(-MAX_HISTORY),
            uptime:       now - startTime.current,
            processes:    (p.process_count ?? prev.processes) as number,
            ping:         (p.ping_ms       ?? prev.ping) as number,
            threatLevel:  cpu > 80 ? 'high' : cpu > 50 ? 'medium' : 'low',
            auditMeta:    (msg.state as Record<string, unknown>).audit_meta ?? prev.auditMeta,
          }));
        }
      } catch (error) {
        wsErr('Failed to parse payload:', error);
      }
    };

    socket.onclose = () => {
      stopPing();
      setIsOnline(false);
      useConnectionStore.getState().setCoreOnline(false);
      if (!mountedRef.current) return;
      const delay = Math.min(retryDelay.current, RECONNECT_MAX_MS);
      retryDelay.current = Math.min(retryDelay.current * 1.5, RECONNECT_MAX_MS);
      wsWarn(`Reconnecting in ${Math.round(delay / 1000)}s…`);
      setTimeout(connect, delay);
    };

    socket.onerror = () => {
      wsErr('socket error');
      socket.close();
    };
  }, [stopPing]);  // stable — no state deps

  useEffect(() => {
    mountedRef.current = true;
    connect();
    return () => {
      mountedRef.current = false;
      stopPing();
      ws.current?.close(1000, 'component unmount');
    };
  }, [connect, stopPing]);

  return { ...metrics, isOnline };
}

