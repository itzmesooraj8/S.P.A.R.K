/**
 * useWakeWordListener Hook
 * ────────────────────────────────────────────────────────────────────────────────
 * Listens for WAKE_WORD_DETECTED WebSocket events and opens the Command Bar.
 * Automatically starts microphone recording for hands-free voice commands.
 */

import { useEffect, useRef, useCallback } from 'react';
import { useConnectionStore } from '@/store/useConnectionStore';
import { useCommandBarStore } from '@/store/commandBarStore';
import { useVoiceMic } from './useVoiceMic';
import { buildAuthedWsUrl } from '@/lib/wsAuth';

const RECONNECT_BASE_MS = 3_000;
const RECONNECT_MAX_MS  = 30_000;

export function useWakeWordListener() {
  const ws         = useRef<WebSocket | null>(null);
  const retryDelay = useRef(RECONNECT_BASE_MS);
  const mountedRef = useRef(true);
  const retryNonce = useConnectionStore((s) => s.retryNonce);

  const { setOpen } = useCommandBarStore();
  const { startRecording } = useVoiceMic();

  const connect = useCallback(() => {
    if (!mountedRef.current) return;
    if (ws.current && ws.current.readyState <= WebSocket.OPEN) return;

    const socket = new WebSocket(buildAuthedWsUrl('/ws/system'));
    ws.current = socket;

    socket.onmessage = (event: MessageEvent) => {
      try {
        const message = JSON.parse(event.data as string);
        if (message.type === 'WAKE_WORD_DETECTED') {
          console.log(
            `🎤 Wake word detected: "${message.wake_word}" (confidence: ${(message.confidence * 100).toFixed(0)}%)`
          );
          setOpen(true);
          setTimeout(() => {
            startRecording();
          }, 100);
        }
      } catch {
        // Not JSON or unrelated frame — ignore
      }
    };

    socket.onopen = () => {
      if (!mountedRef.current) { socket.close(); return; }
      retryDelay.current = RECONNECT_BASE_MS;
    };

    socket.onclose = () => {
      if (!mountedRef.current) return;
      const delay = retryDelay.current;
      retryDelay.current = Math.min(delay * 2, RECONNECT_MAX_MS);
      setTimeout(connect, delay);
    };
  }, [setOpen, startRecording]);

  useEffect(() => {
    mountedRef.current = true;
    connect();
    return () => {
      mountedRef.current = false;
      ws.current?.close(1000, 'unmount');
      ws.current = null;
    };
  }, [connect, retryNonce]);
}

