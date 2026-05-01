import { useState, useCallback, useRef, useEffect } from 'react';
import { AiWsMessage } from '../types/contracts';
import { buildAuthedWsUrl, hasValidAccessToken, shouldReconnectAfterClose } from '../lib/wsAuth';

const VERBOSE_WS = import.meta.env.VITE_VERBOSE_WS === 'true';
const wsLog  = (...a: unknown[]) => VERBOSE_WS && console.log('[VoiceEngine WS]',  ...a);
const wsWarn = (...a: unknown[]) => VERBOSE_WS && console.warn('[VoiceEngine WS]', ...a);
const wsErr  = (...a: unknown[]) => VERBOSE_WS && console.error('[VoiceEngine WS]', ...a);

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000';

const RECONNECT_BASE_MS = 1200;
const RECONNECT_MAX_MS = 15000;
const STT_FINAL_TIMEOUT_MS = 9000;

function buildSttWsUrl(path: string): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  try {
    const base = new URL(API_BASE);
    const protocol = base.protocol === 'https:' ? 'wss:' : 'ws:';
    return new URL(normalizedPath, `${protocol}//${base.host}`).toString();
  } catch {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const port = import.meta.env.VITE_BACKEND_PORT ?? '8000';
    return `${protocol}//${window.location.hostname}:${port}${normalizedPath}`;
  }
}

function suffixFromMimeType(mimeType: string): string {
  const normalized = (mimeType || '').toLowerCase();
  if (normalized.includes('webm')) return '.webm';
  if (normalized.includes('mpeg') || normalized.includes('mp3')) return '.mp3';
  if (normalized.includes('ogg')) return '.ogg';
  if (normalized.includes('mp4')) return '.mp4';
  return '.wav';
}

export type AiStatus = 'idle' | 'listening' | 'thinking' | 'responding';

export interface CommandEntry {
  id: string;
  type: 'user' | 'ai';
  text: string;
  timestamp: Date;
}

export interface TtsPlaybackState {
  speaking: boolean;
  progress: number;
  currentSec: number;
  durationSec: number;
  engine: string;
}

// ── TTS Helper ─────────────────────────────────────────────────────────────────
let _currentAudio: HTMLAudioElement | null = null;
let _ttsQueue: string[] = [];
let _isSpeaking = false;

const _ttsListeners = new Set<(state: TtsPlaybackState) => void>();
let _ttsState: TtsPlaybackState = {
  speaking: false,
  progress: 0,
  currentSec: 0,
  durationSec: 0,
  engine: 'unknown',
};

function _emitTtsState(next: Partial<TtsPlaybackState>) {
  _ttsState = { ..._ttsState, ...next };
  _ttsListeners.forEach((listener) => {
    try {
      listener(_ttsState);
    } catch {
      // ignore listener failures
    }
  });
}

function _subscribeTtsState(listener: (state: TtsPlaybackState) => void) {
  _ttsListeners.add(listener);
  listener(_ttsState);
  return () => {
    _ttsListeners.delete(listener);
  };
}

async function _playNextInQueue(): Promise<void> {
  if (_isSpeaking || _ttsQueue.length === 0) return;

  _isSpeaking = true;
  const text = _ttsQueue.shift();
  if (!text) {
    _isSpeaking = false;
    return;
  }

  try {
    const response = await fetch(`${API_BASE}/api/voice/speak`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: text.slice(0, 800), // Limit text length for TTS
        voice: 'en-US-GuyNeural',
        rate: '+5%',
        pitch: '-10Hz',
      }),
    });

    if (!response.ok) {
      _isSpeaking = false;
      _emitTtsState({ speaking: false, progress: 0, currentSec: 0, durationSec: 0 });
      _playNextInQueue(); // Try next item
      return;
    }

    const engine = response.headers.get('X-Engine') || 'unknown';
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    _currentAudio = audio;

    _emitTtsState({
      speaking: true,
      progress: 0,
      currentSec: 0,
      durationSec: 0,
      engine,
    });

    audio.onloadedmetadata = () => {
      const duration = Number.isFinite(audio.duration) ? audio.duration : 0;
      _emitTtsState({ durationSec: duration });
    };

    audio.ontimeupdate = () => {
      const duration = Number.isFinite(audio.duration) ? audio.duration : 0;
      const current = Number.isFinite(audio.currentTime) ? audio.currentTime : 0;
      const progress = duration > 0 ? Math.min(1, current / duration) : 0;
      _emitTtsState({ currentSec: current, durationSec: duration, progress });
    };

    // When this audio finishes, play the next one
    audio.onended = () => {
      URL.revokeObjectURL(url);
      _currentAudio = null;
      _isSpeaking = false;
      _emitTtsState({ speaking: false, progress: 1, currentSec: 0, durationSec: 0 });
      _playNextInQueue();
    };

    audio.onerror = () => {
      URL.revokeObjectURL(url);
      _currentAudio = null;
      _isSpeaking = false;
      _emitTtsState({ speaking: false, progress: 0, currentSec: 0, durationSec: 0 });
      _playNextInQueue();
    };

    audio.play().catch(() => {
      _isSpeaking = false;
      URL.revokeObjectURL(url);
      _emitTtsState({ speaking: false, progress: 0, currentSec: 0, durationSec: 0 });
      _playNextInQueue();
    });
  } catch (err) {
    wsWarn('TTS error:', err);
    _isSpeaking = false;
    _emitTtsState({ speaking: false, progress: 0, currentSec: 0, durationSec: 0 });
    _playNextInQueue();
  }
}

async function speakText(
  text: string,
  _options?: { rate?: number; pitch?: number; voice?: string }
): Promise<void> {
  // Stop any currently playing TTS (new messages override old ones)
  if (_currentAudio) {
    _currentAudio.pause();
    _currentAudio = null;
  }

  if (!text.trim()) return;

  // Add to queue
  _ttsQueue = [text]; // Clear queue and add new message (override old)
  _playNextInQueue();
}

export function stopTTS() {
  if (_currentAudio) {
    _currentAudio.pause();
    _currentAudio = null;
  }
  _ttsQueue = [];
  _isSpeaking = false;
  _emitTtsState({ speaking: false, progress: 0, currentSec: 0, durationSec: 0 });
}

export function useVoiceEngine() {
  const [status, setStatus] = useState<AiStatus>('idle');
  const [isListening, setIsListening] = useState(false);
  const [isOnline, setIsOnline] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [aiResponse, setAiResponse] = useState('');
  const [ttsEnabled, setTtsEnabled] = useState(true); // SPARK speaks by default
  const [commandHistory, setCommandHistory] = useState<CommandEntry[]>([
    { id: '0', type: 'ai', text: 'SPARK v4.1 Sovereign Core initialized. Awaiting input.', timestamp: new Date() },
  ]);
  const [amplitude, setAmplitude] = useState<number[]>(new Array(32).fill(0));
  const [ttsPlayback, setTtsPlayback] = useState<TtsPlaybackState>(_ttsState);

  const analyserRef = useRef<AnalyserNode | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const animFrameRef = useRef<number>(0);
  const streamRef = useRef<MediaStream | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const sttSocketRef = useRef<WebSocket | null>(null);
  const sttChunksRef = useRef<Blob[]>([]);
  const sttMimeTypeRef = useRef('audio/webm');
  const sttFinalPendingRef = useRef(false);
  const sttFinalTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Real WebSocket Reference
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const retryDelayRef = useRef(RECONNECT_BASE_MS);
  const outboundQueueRef = useRef<string[]>([]);
  const awaitingResponseRef = useRef(false);
  const mountedRef = useRef(true);
  const ttsEnabledRef = useRef(ttsEnabled);
  const aiResponseRef = useRef('');
  const isListeningRef = useRef(isListening);

  const addEntry = useCallback((type: 'user' | 'ai', text: string) => {
    setCommandHistory(prev => [...prev.slice(-49), {
      id: Date.now().toString(),
      type, text,
      timestamp: new Date(),
    }]);
  }, []);

  useEffect(() => {
    ttsEnabledRef.current = ttsEnabled;
  }, [ttsEnabled]);

  useEffect(() => {
    aiResponseRef.current = aiResponse;
  }, [aiResponse]);

  useEffect(() => {
    isListeningRef.current = isListening;
  }, [isListening]);

  useEffect(() => {
    return _subscribeTtsState(setTtsPlayback);
  }, []);

  const finishStreamingResponse = useCallback((opts?: { errorMessage?: string; skipTts?: boolean }) => {
    awaitingResponseRef.current = false;
    setStatus(isListeningRef.current ? 'listening' : 'idle');

    const finalMessage = aiResponseRef.current.trim();
    aiResponseRef.current = '';
    setAiResponse('');

    if (finalMessage) {
      addEntry('ai', finalMessage);
      if (ttsEnabledRef.current && !opts?.skipTts) {
        speakText(finalMessage).catch(() => {});
      }
    }

    if (opts?.errorMessage) {
      addEntry('ai', opts.errorMessage);
    }
  }, [addEntry]);

  const flushSendQueue = useCallback(() => {
    const socket = wsRef.current;
    if (!socket || socket.readyState !== WebSocket.OPEN) return;

    while (outboundQueueRef.current.length > 0) {
      const payload = outboundQueueRef.current.shift();
      if (payload) socket.send(payload);
    }
  }, []);

  const connectWS = useCallback(() => {
    if (!mountedRef.current) return;
    if (wsRef.current && (wsRef.current.readyState === WebSocket.CONNECTING || wsRef.current.readyState === WebSocket.OPEN)) {
      return;
    }
    if (!hasValidAccessToken()) {
      setIsOnline(false);
      return;
    }

    const ws = new WebSocket(buildAuthedWsUrl('/ws/ai'));
    wsRef.current = ws;

    ws.onopen = () => {
      if (!mountedRef.current) {
        ws.close(1000, 'component unmounted');
        return;
      }
      setIsOnline(true);
      retryDelayRef.current = RECONNECT_BASE_MS;
      wsLog('AI socket connected.');
      flushSendQueue();
    };

    ws.onmessage = (event) => {
      try {
        if (typeof event.data !== 'string') return;
        const data: AiWsMessage = JSON.parse(event.data);
        const messageType = String((data as { type?: unknown }).type || '');

        if (messageType === 'response_token' || messageType === 'TOKEN') {
          const token = typeof data.token === 'string'
            ? data.token
            : typeof data.content === 'string'
              ? data.content
              : '';

          if (!token) return;
          setStatus('responding');
          setAiResponse((prev) => {
            const next = prev + token;
            aiResponseRef.current = next;
            return next;
          });
          return;
        }

        if (messageType === 'response_done' || messageType === 'DONE') {
          finishStreamingResponse();
          return;
        }

        if (messageType === 'tool_execute' || messageType === 'TOOL_EXECUTE') {
          addEntry('ai', `[TOOL] Executing ${data.tool || 'unknown'}...`);
          return;
        }

        if (messageType === 'error' || messageType === 'ERROR') {
          const legacy = typeof data.content === 'string' ? data.content : '';
          const modern = typeof (data as unknown as { message?: unknown }).message === 'string'
            ? ((data as unknown as { message: string }).message)
            : '';
          const msg = (legacy || modern).trim() || 'Unknown error';
          finishStreamingResponse({ errorMessage: `[ERROR] ${msg}`, skipTts: true });
        }
      } catch (err) {
        wsErr('Error parsing WS message:', err);
      }
    };

    ws.onclose = (event) => {
      setIsOnline(false);
      wsRef.current = null;

      if (awaitingResponseRef.current) {
        finishStreamingResponse({
          errorMessage: '[ERROR] Connection dropped before completion. Reconnecting...',
          skipTts: true,
        });
      }

      if (!mountedRef.current) return;
      if (!shouldReconnectAfterClose(event.code)) {
        wsWarn('AI socket auth unavailable; waiting for fresh login before reconnect.');
        return;
      }

      const baseDelay = Math.min(retryDelayRef.current, RECONNECT_MAX_MS);
      const jitter = Math.floor(Math.random() * 350);
      const delay = baseDelay + jitter;
      retryDelayRef.current = Math.min(Math.round(baseDelay * 1.7), RECONNECT_MAX_MS);

      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      wsWarn(`AI socket closed (${event.code}). Reconnecting in ${Math.round(delay / 1000)}s...`);
      reconnectTimerRef.current = setTimeout(() => {
        reconnectTimerRef.current = null;
        connectWS();
      }, delay);
    };

    ws.onerror = (e) => {
      wsErr('WS Error:', e);
      ws.close();
    };
  }, [addEntry, finishStreamingResponse, flushSendQueue]);

  useEffect(() => {
    mountedRef.current = true;
    connectWS();

    return () => {
      mountedRef.current = false;
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      if (wsRef.current) wsRef.current.close(1000, 'component unmount');
    };
  }, [connectWS]);

  const sendUserMessage = useCallback((raw: string) => {
    const message = raw.trim();
    if (!message) return;
    if (awaitingResponseRef.current) return;

    addEntry('user', message);
    setStatus('thinking');
    aiResponseRef.current = '';
    setAiResponse('');
    awaitingResponseRef.current = true;

    const payload = JSON.stringify({ message });
    const socket = wsRef.current;

    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(payload);
      return;
    }

    outboundQueueRef.current.push(payload);
    addEntry('ai', '[SYSTEM] AI core reconnecting. Command queued...');
    connectWS();
  }, [addEntry, connectWS]);

  const processInput = useCallback((input: string) => {
    sendUserMessage(input);
  }, [sendUserMessage]);

  // ---------- Microphone / Audio Architecture ----------

  const clearSttFinalTimer = useCallback(() => {
    if (sttFinalTimerRef.current) {
      clearTimeout(sttFinalTimerRef.current);
      sttFinalTimerRef.current = null;
    }
  }, []);

  const closeSttSocket = useCallback(() => {
    clearSttFinalTimer();
    sttFinalPendingRef.current = false;

    const socket = sttSocketRef.current;
    if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
      try {
        socket.close(1000, 'stt complete');
      } catch {
        // ignore socket close race
      }
    }
    sttSocketRef.current = null;
  }, [clearSttFinalTimer]);

  const stopAmplitudeTracking = useCallback(() => {
    cancelAnimationFrame(animFrameRef.current);
    setAmplitude(new Array(32).fill(0));
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop());
      streamRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close().catch(() => {});
      audioContextRef.current = null;
    }
    analyserRef.current = null;
  }, []);

  const startAmplitudeTracking = useCallback(async (): Promise<MediaStream> => {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });

    streamRef.current = stream;

    if (audioContextRef.current) {
      audioContextRef.current.close().catch(() => {});
    }

    const ctx = new AudioContext();
    audioContextRef.current = ctx;
    const source = ctx.createMediaStreamSource(stream);
    const analyser = ctx.createAnalyser();
    analyser.fftSize = 64;
    source.connect(analyser);
    analyserRef.current = analyser;

    const data = new Uint8Array(analyser.frequencyBinCount);
    const tick = () => {
      analyser.getByteFrequencyData(data);
      setAmplitude(Array.from(data).slice(0, 32).map((v) => v / 255));
      animFrameRef.current = requestAnimationFrame(tick);
    };
    tick();

    return stream;
  }, []);

  const transcribeViaHttp = useCallback(async (audioBlob: Blob): Promise<string> => {
    const formData = new FormData();
    formData.append('file', audioBlob, `recording${suffixFromMimeType(audioBlob.type)}`);
    formData.append('language', 'en');

    const response = await fetch(`${API_BASE}/api/voice/transcribe`, {
      method: 'POST',
      body: formData,
    });

    const payload = (await response.json()) as {
      success?: boolean;
      text?: string;
      error?: string;
    };

    if (!response.ok || !payload.success) {
      throw new Error(payload.error || `STT request failed (${response.status})`);
    }

    return (payload.text || '').trim();
  }, []);

  const finalizeWithFallback = useCallback(async () => {
    const chunks = sttChunksRef.current.slice();
    closeSttSocket();

    if (chunks.length === 0) {
      addEntry('ai', '[ERROR] No microphone audio captured.');
      setStatus('idle');
      return;
    }

    try {
      const blob = new Blob(chunks, { type: sttMimeTypeRef.current || 'audio/webm' });
      const text = await transcribeViaHttp(blob);
      setTranscript(text);

      if (text) {
        processInput(text);
      } else {
        setStatus('idle');
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Transcription failed.';
      addEntry('ai', `[ERROR] ${message}`);
      setStatus('idle');
    } finally {
      sttChunksRef.current = [];
    }
  }, [addEntry, closeSttSocket, processInput, transcribeViaHttp]);

  const stopListening = useCallback(() => {
    isListeningRef.current = false;
    setIsListening(false);

    const recorder = mediaRecorderRef.current;
    if (!recorder || recorder.state === 'inactive') {
      stopAmplitudeTracking();
      closeSttSocket();
      setStatus((prev) => {
        if (prev === 'thinking' || prev === 'responding') {
          return prev;
        }
        return 'idle';
      });
      return;
    }

    setStatus('thinking');

    recorder.onstop = () => {
      stopAmplitudeTracking();
      mediaRecorderRef.current = null;

      const socket = sttSocketRef.current;
      if (socket && socket.readyState === WebSocket.OPEN) {
        sttFinalPendingRef.current = true;
        socket.send(
          JSON.stringify({
            action: 'transcribe',
            language: 'en',
            suffix: suffixFromMimeType(sttMimeTypeRef.current),
          }),
        );

        clearSttFinalTimer();
        sttFinalTimerRef.current = setTimeout(() => {
          if (!sttFinalPendingRef.current) return;
          sttFinalPendingRef.current = false;
          void finalizeWithFallback();
        }, STT_FINAL_TIMEOUT_MS);
        return;
      }

      void finalizeWithFallback();
    };

    recorder.stop();
  }, [clearSttFinalTimer, closeSttSocket, finalizeWithFallback, stopAmplitudeTracking]);

  const startListening = useCallback(async () => {
    if (typeof MediaRecorder === 'undefined') {
      addEntry('ai', '[ERROR] MediaRecorder is not supported in this browser.');
      return;
    }

    closeSttSocket();
    sttChunksRef.current = [];
    setTranscript('');

    try {
      const stream = await startAmplitudeTracking();
      const mimeType = MediaRecorder.isTypeSupported('audio/ogg;codecs=opus')
        ? 'audio/ogg;codecs=opus'
        : (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
            ? 'audio/webm;codecs=opus'
            : (MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : 'audio/mp4'));

      sttMimeTypeRef.current = mimeType;

      const socket = new WebSocket(buildSttWsUrl('/api/voice/transcribe/ws'));
      sttSocketRef.current = socket;
      const wsChunkQueue: Blob[] = [];

      socket.onopen = () => {
        while (wsChunkQueue.length > 0) {
          const chunk = wsChunkQueue.shift();
          if (!chunk) break;
          socket.send(chunk);
        }
      };

      socket.onmessage = (event) => {
        if (typeof event.data !== 'string') {
          return;
        }

        try {
          const frame = JSON.parse(event.data) as {
            type?: string;
            text?: string;
            message?: string;
          };

          if (frame.type === 'final') {
            sttFinalPendingRef.current = false;
            clearSttFinalTimer();
            const text = (frame.text || '').trim();
            setTranscript(text);
            closeSttSocket();
            sttChunksRef.current = [];

            if (text) {
              processInput(text);
            } else {
              setStatus('idle');
            }
            return;
          }

          if (frame.type === 'error') {
            sttFinalPendingRef.current = false;
            clearSttFinalTimer();
            const message = (frame.message || 'Unknown transcription error').trim();
            wsWarn('STT WS error. Falling back to HTTP transcription:', message);
            closeSttSocket();
            void finalizeWithFallback();
          }
        } catch {
          // ignore malformed STT frames
        }
      };

      socket.onclose = () => {
        if (!sttFinalPendingRef.current) {
          return;
        }
        sttFinalPendingRef.current = false;
        clearSttFinalTimer();
        void finalizeWithFallback();
      };

      const recorder = new MediaRecorder(stream, {
        mimeType,
        audioBitsPerSecond: 128000,
      });
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (!event.data || event.data.size === 0) {
          return;
        }

        sttChunksRef.current.push(event.data);
        const sttSocket = sttSocketRef.current;
        if (sttSocket && sttSocket.readyState === WebSocket.OPEN) {
          sttSocket.send(event.data);
        } else {
          wsChunkQueue.push(event.data);
        }
      };

      recorder.onerror = () => {
        addEntry('ai', '[ERROR] Microphone recording failed.');
        stopListening();
      };

      recorder.start(250);
      isListeningRef.current = true;
      setIsListening(true);
      setStatus((prev) => (prev === 'thinking' || prev === 'responding') ? prev : 'listening');
    } catch {
      stopAmplitudeTracking();
      closeSttSocket();
      addEntry('ai', '[ERROR] Microphone access denied or unavailable.');
      setStatus('idle');
    }
  }, [addEntry, clearSttFinalTimer, closeSttSocket, finalizeWithFallback, processInput, startAmplitudeTracking, stopAmplitudeTracking, stopListening]);

  const toggleMic = useCallback(async () => {
    if (isListeningRef.current) {
      stopListening();
      return;
    }
    await startListening();
  }, [startListening, stopListening]);

  const cancelGeneration = useCallback(() => {
    awaitingResponseRef.current = false;
    aiResponseRef.current = '';
    setAiResponse('');
    setStatus(isListeningRef.current ? 'listening' : 'idle');

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'CANCEL' }));
    }
  }, []);

  useEffect(() => {
    return () => {
      isListeningRef.current = false;
      const recorder = mediaRecorderRef.current;
      if (recorder && recorder.state !== 'inactive') {
        try {
          recorder.stop();
        } catch {
          // ignore recorder teardown race
        }
      }
      closeSttSocket();
      stopAmplitudeTracking();
    };
  }, [closeSttSocket, stopAmplitudeTracking]);

  return {
    status, isListening, isOnline, transcript,
    aiResponse, commandHistory, amplitude,
    ttsPlayback,
    ttsEnabled, setTtsEnabled,
    toggleMic, processInput, cancelGeneration,
    speakText,
  };
}
