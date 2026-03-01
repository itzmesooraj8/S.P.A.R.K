/**
 * useAIEvents
 * ─────────────────────────────────────────────────────────────────────────────
 * Connects to /ws/ai and forwards TOOL_EXECUTE + TOOL_RESULT frames into
 * useToolActivityStore so ToolActivityPanel stays live.
 *
 * Mount this once in HudLayout so the store fills regardless of which panel
 * is open.
 */

import { useEffect, useRef, useCallback } from 'react';
import { useToolActivityStore } from '@/store/useToolActivityStore';
import { useConnectionStore } from '@/store/useConnectionStore';

const VERBOSE_WS = import.meta.env.VITE_VERBOSE_WS === 'true';
const wsWarn = (...a: unknown[]) => VERBOSE_WS && console.warn('[AIEvents WS]', ...a);

const WS_URL = (() => {
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
  const port  = import.meta.env.VITE_BACKEND_PORT ?? '8000';
  return `${proto}://${window.location.hostname}:${port}/ws/ai`;
})();

const RECONNECT_BASE_MS = 3_000;
const RECONNECT_MAX_MS  = 30_000;

export function useAIEvents() {
  const ws         = useRef<WebSocket | null>(null);
  const retryDelay = useRef(RECONNECT_BASE_MS);
  const mountedRef = useRef(true);
  const { addExecute, addResult } = useToolActivityStore();

  const connect = useCallback(() => {
    if (!mountedRef.current) return;
    if (ws.current && ws.current.readyState <= WebSocket.OPEN) return;

    const socket = new WebSocket(WS_URL);
    ws.current = socket;

    socket.onmessage = (event: MessageEvent) => {
      try {
        const msg = JSON.parse(event.data as string);
        if (msg.type === 'TOOL_EXECUTE') {
          addExecute(msg.tool, msg.arguments);
        } else if (msg.type === 'TOOL_RESULT') {
          const status = msg.status === 'error' ? 'error' : 'success';
          addResult(msg.tool, status, msg.output, msg.error);
        }
      } catch {
        // ignore malformed frames
      }
    };

    socket.onopen = () => {
      retryDelay.current = RECONNECT_BASE_MS;
      useConnectionStore.getState().setAiOnline(true);
    };

    socket.onclose = () => {
      useConnectionStore.getState().setAiOnline(false);
      if (!mountedRef.current) return;
      const delay = Math.min(retryDelay.current, RECONNECT_MAX_MS);
      retryDelay.current = Math.min(retryDelay.current * 1.5, RECONNECT_MAX_MS);
      wsWarn(`Reconnecting in ${Math.round(delay / 1000)}s…`);
      setTimeout(connect, delay);
    };

    socket.onerror = () => socket.close();
  }, [addExecute, addResult]);

  useEffect(() => {
    mountedRef.current = true;
    connect();
    return () => {
      mountedRef.current = false;
      ws.current?.close(1000, 'unmount');
    };
  }, [connect]);
}
