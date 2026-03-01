/**
 * useGlobeSocket — real-time WebSocket consumer for /ws/globe
 *
 * Server push message types:
 *   GLOBE_DELTA   → new/updated events for a named layer
 *   GLOBE_TICKER  → market / financial tick updates
 *   GLOBE_FUSION  → Signal Fusion correlation alerts
 *   GLOBE_HEALTH  → provider circuit-breaker health
 *   pong          → keep-alive response
 */
import { useEffect, useRef, useCallback } from 'react';
import { useMonitorStore } from '../store/useMonitorStore';

const VERBOSE_WS = import.meta.env.VITE_VERBOSE_WS === 'true';
const wsWarn = (...a: unknown[]) => VERBOSE_WS && console.warn('[Globe WS]', ...a);

const WS_URL = (() => {
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
  const port  = import.meta.env.VITE_BACKEND_PORT ?? '8000';
  return `${proto}://${window.location.hostname}:${port}/ws/globe`;
})();

const RECONNECT_BASE_MS  = 2_000;
const RECONNECT_MAX_MS   = 30_000;
const PING_INTERVAL_MS   = 20_000;

export function useGlobeSocket() {
  const ws          = useRef<WebSocket | null>(null);
  const retryDelay  = useRef(RECONNECT_BASE_MS);
  const pingTimer   = useRef<ReturnType<typeof setInterval> | null>(null);
  const mountedRef  = useRef(true);

  const setWsConnected  = useMonitorStore((s) => s.setWsConnected);
  const mergeGlobeDelta = useMonitorStore((s) => s.mergeGlobeDelta);
  const setGlobeTickers = useMonitorStore((s) => s.setGlobeTickers);
  const setProviderHealth = useMonitorStore.getState;   // stable ref

  const stopPing = useCallback(() => {
    if (pingTimer.current) {
      clearInterval(pingTimer.current);
      pingTimer.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    if (!mountedRef.current) return;
    if (ws.current && ws.current.readyState <= WebSocket.OPEN) return;

    const socket = new WebSocket(WS_URL);
    ws.current = socket;

    socket.onopen = () => {
      if (!mountedRef.current) { socket.close(); return; }
      console.info('[Globe WS] Connected');
      setWsConnected(true);
      retryDelay.current = RECONNECT_BASE_MS;

      // Keep-alive ping
      stopPing();
      pingTimer.current = setInterval(() => {
        if (socket.readyState === WebSocket.OPEN) {
          socket.send('ping');
        }
      }, PING_INTERVAL_MS);
    };

    socket.onmessage = (ev: MessageEvent) => {
      try {
        const msg = JSON.parse(ev.data as string);
        switch (msg.type) {
          case 'GLOBE_DELTA':
            mergeGlobeDelta(msg.layer, msg.events ?? []);
            break;
          case 'GLOBE_TICKER':
            setGlobeTickers(msg.tickers ?? []);
            break;
          case 'GLOBE_HEALTH': {
            const store = useMonitorStore.getState();
            store.fetchProviderHealth?.();           // re-use existing action
            break;
          }
          case 'GLOBE_FUSION': {
            // Fusion items handled by the existing store action;
            // a WS push simply triggers a refresh
            useMonitorStore.getState().fetchFusionSummary?.();
            break;
          }
          // 'pong' — no-op
        }
      } catch {
        // Ignore malformed frames
      }
    };

    socket.onerror = () => {
      wsWarn('socket error');
    };

    socket.onclose = () => {
      stopPing();
      setWsConnected(false);
      if (!mountedRef.current) return;
      const delay = Math.min(retryDelay.current, RECONNECT_MAX_MS);
      retryDelay.current = Math.min(retryDelay.current * 1.5, RECONNECT_MAX_MS);
      console.info(`[Globe WS] Reconnecting in ${Math.round(delay / 1000)}s…`);
      setTimeout(connect, delay);
    };
  }, [mergeGlobeDelta, setGlobeTickers, setWsConnected, stopPing]);

  useEffect(() => {
    mountedRef.current = true;
    connect();
    return () => {
      mountedRef.current = false;
      stopPing();
      ws.current?.close(1000, 'component unmount');
    };
  }, [connect, stopPing]);
}
