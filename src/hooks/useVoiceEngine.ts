import { useState, useCallback, useRef, useEffect } from 'react';
import { AiWsMessage } from '../types/contracts';
import { buildAuthedWsUrl } from '../lib/wsAuth';

const VERBOSE_WS = import.meta.env.VITE_VERBOSE_WS === 'true';
const wsLog  = (...a: unknown[]) => VERBOSE_WS && console.log('[VoiceEngine WS]',  ...a);
const wsWarn = (...a: unknown[]) => VERBOSE_WS && console.warn('[VoiceEngine WS]', ...a);
const wsErr  = (...a: unknown[]) => VERBOSE_WS && console.error('[VoiceEngine WS]', ...a);

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000';

const RECONNECT_BASE_MS = 1200;
const RECONNECT_MAX_MS = 15000;

export type AiStatus = 'idle' | 'listening' | 'thinking' | 'responding';

export interface CommandEntry {
  id: string;
  type: 'user' | 'ai';
  text: string;
  timestamp: Date;
}

// ── TTS Helper ─────────────────────────────────────────────────────────────────
let _currentAudio: HTMLAudioElement | null = null;
let _ttsQueue: string[] = [];
let _isSpeaking = false;

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
      _playNextInQueue(); // Try next item
      return;
    }

    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    _currentAudio = audio;

    // When this audio finishes, play the next one
    audio.onended = () => {
      URL.revokeObjectURL(url);
      _currentAudio = null;
      _isSpeaking = false;
      _playNextInQueue();
    };

    audio.onerror = () => {
      URL.revokeObjectURL(url);
      _currentAudio = null;
      _isSpeaking = false;
      _playNextInQueue();
    };

    audio.play().catch(() => {
      _isSpeaking = false;
      URL.revokeObjectURL(url);
      _playNextInQueue();
    });
  } catch (err) {
    wsWarn('TTS error:', err);
    _isSpeaking = false;
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

  const recognitionRef = useRef<any>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const animFrameRef = useRef<number>(0);
  const streamRef = useRef<MediaStream | null>(null);

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

        if (data.type === 'response_token' || data.type === 'TOKEN') {
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

        if (data.type === 'response_done' || data.type === 'DONE') {
          finishStreamingResponse();
          return;
        }

        if (data.type === 'tool_execute' || data.type === 'TOOL_EXECUTE') {
          addEntry('ai', `[TOOL] Executing ${data.tool || 'unknown'}...`);
          return;
        }

        if (data.type === 'error' || data.type === 'ERROR') {
          const legacy = typeof data.content === 'string' ? data.content : '';
          const modern = typeof (data as { message?: unknown }).message === 'string'
            ? ((data as { message: string }).message)
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

  const startAmplitudeTracking = useCallback(async (): Promise<void> => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
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
        setAmplitude(Array.from(data).slice(0, 32).map(v => v / 255));
        animFrameRef.current = requestAnimationFrame(tick);
      };
      tick();
    } catch {
      const tick = () => {
        setAmplitude(new Array(32).fill(0).map(() => Math.random() * 0.6));
        animFrameRef.current = requestAnimationFrame(tick);
      };
      tick();
    }
  }, []);

  const stopListening = useCallback(() => {
    isListeningRef.current = false;
    setIsListening(false);
    recognitionRef.current?.stop?.();
    recognitionRef.current?.abort?.();
    stopAmplitudeTracking();

    setStatus((prev) => {
      if (prev === 'thinking' || prev === 'responding') {
        return prev;
      }
      return 'idle';
    });
  }, [stopAmplitudeTracking]);

  const startListening = useCallback(async () => {
    const SpeechRecognitionAPI = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognitionAPI) {
      addEntry('ai', '[ERROR] Speech recognition not supported by browser viewport.');
      return;
    }

    const recognition = new SpeechRecognitionAPI();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';
    recognitionRef.current = recognition;

    recognition.onstart = () => {
      isListeningRef.current = true;
      setIsListening(true);
      setStatus((prev) => (prev === 'thinking' || prev === 'responding') ? prev : 'listening');
    };

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      const result = event.results[event.results.length - 1];
      const text = result[0].transcript;
      setTranscript(text);
      if (result.isFinal) {
        setTranscript('');
        processInput(text);
      }
    };

    recognition.onerror = () => {
      stopListening();
    };

    recognition.onend = () => {
      if (isListeningRef.current) {
        recognition.start();
        return;
      }
      setStatus((prev) => (prev === 'thinking' || prev === 'responding') ? prev : 'idle');
    };

    recognition.start();
    await startAmplitudeTracking();
  }, [addEntry, processInput, startAmplitudeTracking, stopListening]);

  const toggleMic = useCallback(async () => {
    if (isListeningRef.current) {
      stopListening();
      return;
    }
    isListeningRef.current = true;
    setIsListening(true);
    try {
      await startListening();
    } catch {
      stopListening();
    }
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
      stopAmplitudeTracking();
      recognitionRef.current?.stop();
      recognitionRef.current?.abort?.();
    };
  }, [stopAmplitudeTracking]);

  return {
    status, isListening, isOnline, transcript,
    aiResponse, commandHistory, amplitude,
    ttsEnabled, setTtsEnabled,
    toggleMic, processInput, cancelGeneration,
    speakText,
  };
}
