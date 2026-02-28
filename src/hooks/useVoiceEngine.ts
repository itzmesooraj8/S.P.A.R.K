import { useState, useCallback, useRef, useEffect } from 'react';
import { AiWsMessage } from '../types/contracts';

export type AiStatus = 'idle' | 'listening' | 'thinking' | 'responding';

export interface CommandEntry {
  id: string;
  type: 'user' | 'ai';
  text: string;
  timestamp: Date;
}

export function useVoiceEngine() {
  const [status, setStatus] = useState<AiStatus>('idle');
  const [isListening, setIsListening] = useState(false);
  const [isOnline, setIsOnline] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [aiResponse, setAiResponse] = useState('');
  const [commandHistory, setCommandHistory] = useState<CommandEntry[]>([
    { id: '0', type: 'ai', text: 'SPARK v4.1 Sovereign Core initialized. Awaiting input.', timestamp: new Date() },
  ]);
  const [amplitude, setAmplitude] = useState<number[]>(new Array(32).fill(0));

  const recognitionRef = useRef<any>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animFrameRef = useRef<number>(0);
  const streamRef = useRef<MediaStream | null>(null);

  // Real WebSocket Reference
  const wsRef = useRef<WebSocket | null>(null);

  const addEntry = useCallback((type: 'user' | 'ai', text: string) => {
    setCommandHistory(prev => [...prev.slice(-49), {
      id: Date.now().toString(),
      type, text,
      timestamp: new Date(),
    }]);
  }, []);

  // Set up WebSocket to /ws/ai on mount
  useEffect(() => {
    let reconnectTimeout: NodeJS.Timeout;

    const connectWS = () => {
      const ws = new WebSocket('ws://localhost:8000/ws/ai');
      wsRef.current = ws;

      ws.onopen = () => {
        setIsOnline(true);
        console.log("[useVoiceEngine] AI socket connected.");
      };

      ws.onmessage = (event) => {
        try {
          const data: AiWsMessage = JSON.parse(event.data);

          if (data.type === 'response_token') {
            // Progressively build the live streaming response
            setStatus('responding');
            setAiResponse((prev) => prev + (data.token || ""));
          } else if (data.type === 'response_done') {
            // Signal streaming completion
            setStatus('idle');

            // Atomically flush the streaming buffer into history to avoid race condition
            setAiResponse((prev) => {
              const finalMessage = prev;

              if (finalMessage.trim() !== '') {
                setCommandHistory((history) => [
                  ...history.slice(-49),
                  {
                    id: Date.now().toString() + Math.random().toString(36).substring(2, 7),
                    type: 'ai',
                    text: finalMessage,
                    timestamp: new Date(),
                  },
                ]);
              }

              return ''; // Clear the streaming buffer
            });
          } else if (data.type === 'tool_execute') {
             addEntry('ai', `[TOOL] Executing ${data.tool || 'unknown'}...`);
          } else if (data.type === 'error') {
             addEntry('ai', `[ERROR] ${data.content || 'Unknown error'}`);
             setStatus('idle');
          }
        } catch (err) {
          console.error('[useVoiceEngine] Error parsing WS message:', err);
        }
      };

      ws.onclose = () => {
        console.warn("[useVoiceEngine] AI socket closed. Reconnecting...");
        setIsOnline(false);
        reconnectTimeout = setTimeout(connectWS, 3000);
      };

      ws.onerror = (e) => {
        console.error("[useVoiceEngine] WS Error:", e);
        ws.close();
      };
    };

    connectWS();

    return () => {
      clearTimeout(reconnectTimeout);
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  const processInput = useCallback((input: string) => {
    if (!input.trim()) return;

    // 1. Add user message
    addEntry('user', input);
    setStatus('thinking');

    // 2. Clear current AI buffer
    setAiResponse('');

    // 3. Send to real backend over WebSocket
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(input);
    } else {
      console.warn("WebSocket not connected. Cannot send prompt.");
      setStatus('idle');
      addEntry('ai', '[ERROR] Sovereign Core disconnected.');
    }
  }, [addEntry]);

  // ---------- Microphone / Audio Architecture ----------

  const stopAmplitudeTracking = useCallback(() => {
    cancelAnimationFrame(animFrameRef.current);
    setAmplitude(new Array(32).fill(0));
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop());
      streamRef.current = null;
    }
    analyserRef.current = null;
  }, []);

  const startAmplitudeTracking = useCallback(async (): Promise<void> => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const ctx = new AudioContext();
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

  const toggleMic = useCallback(async () => {
    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
      setStatus('idle');
      stopAmplitudeTracking();
      return;
    }

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
      setIsListening(true);
      setStatus('listening');
    };

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      const result = event.results[event.results.length - 1];
      const text = result[0].transcript;
      setTranscript(text);
      if (result.isFinal) {
        setTranscript('');
        processInput(text); // Pass directly to backend via processInput
      }
    };

    recognition.onerror = () => {
      setIsListening(false);
      setStatus('idle');
      stopAmplitudeTracking();
    };

    recognition.onend = () => {
      if (isListening) recognition.start();
    };

    recognition.start();
    await startAmplitudeTracking();
  }, [isListening, processInput, startAmplitudeTracking, stopAmplitudeTracking, addEntry]);

  const cancelGeneration = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'CANCEL' }));

      // Optionally stop mic if we were listening, or force status reset
      setStatus('idle');
      setAiResponse((prev) => {
        // Just clear incomplete data without putting it into memory
        return '';
      });
    }
  }, []);

  useEffect(() => {
    return () => {
      stopAmplitudeTracking();
      recognitionRef.current?.stop();
    };
  }, [stopAmplitudeTracking]);

  return {
    status, isListening, isOnline, transcript,
    aiResponse, commandHistory, amplitude,
    toggleMic, processInput, cancelGeneration
  };
}
