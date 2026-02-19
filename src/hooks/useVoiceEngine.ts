import { useState, useCallback, useRef, useEffect } from 'react';

export type AiStatus = 'idle' | 'listening' | 'thinking' | 'responding';

export interface CommandEntry {
  id: string;
  type: 'user' | 'ai';
  text: string;
  timestamp: Date;
}

const AI_RESPONSES: Record<string, string> = {
  default: 'Processing your request. Analyzing neural patterns and cross-referencing quantum databases...',
  weather: 'Current atmospheric conditions: 22°C, partly cloudy. Wind velocity: 12 km/h NE. Probability of precipitation: 18%. All systems nominal.',
  status: 'System status: All modules operational. CPU at optimal load. Threat level: LOW. Firewall integrity: 100%. You are secure.',
  time: `Current chronological reference: ${new Date().toLocaleTimeString()}. Synchronized with atomic clock UTC+0.`,
  hello: 'SPARK AI online. Neural networks fully initialized. How may I assist you today, Commander?',
  help: 'Available commands: STATUS, WEATHER, TIME, SCAN, LOCK, SHUTDOWN. Or speak naturally — I understand context.',
  scan: 'Initiating full system scan. Scanning 4,096 sectors... No threats detected. Firewall: ACTIVE. Encryption: AES-256. All clear.',
  lock: 'Engaging security lockdown protocol. Biometric verification required. Stand by...',
  shutdown: 'Shutdown sequence initiated. Saving system state... Archiving session data... Goodbye, Commander.',
};

function getAiResponse(input: string): string {
  const lower = input.toLowerCase();
  for (const key of Object.keys(AI_RESPONSES)) {
    if (lower.includes(key)) return AI_RESPONSES[key];
  }
  return AI_RESPONSES.default;
}

export function useVoiceEngine() {
  const [status, setStatus] = useState<AiStatus>('idle');
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [aiResponse, setAiResponse] = useState('');
  const [commandHistory, setCommandHistory] = useState<CommandEntry[]>([
    { id: '0', type: 'ai', text: 'SPARK v4.1 initialized. All systems online. Awaiting your command.', timestamp: new Date() },
  ]);
  const [amplitude, setAmplitude] = useState<number[]>(new Array(32).fill(0));
  const recognitionRef = useRef<any>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animFrameRef = useRef<number>(0);
  const streamRef = useRef<MediaStream | null>(null);

  const addEntry = useCallback((type: 'user' | 'ai', text: string) => {
    setCommandHistory(prev => [...prev.slice(-49), {
      id: Date.now().toString(),
      type, text,
      timestamp: new Date(),
    }]);
  }, []);

  const typeResponse = useCallback((text: string) => {
    setStatus('responding');
    setAiResponse('');
    let i = 0;
    const interval = setInterval(() => {
      if (i < text.length) {
        setAiResponse(prev => prev + text[i]);
        i++;
      } else {
        clearInterval(interval);
        setStatus('idle');
        addEntry('ai', text);
      }
    }, 25);
  }, [addEntry]);

  const processInput = useCallback((input: string) => {
    if (!input.trim()) return;
    addEntry('user', input);
    setStatus('thinking');
    setTimeout(() => {
      const response = getAiResponse(input);
      typeResponse(response);
    }, 800 + Math.random() * 700);
  }, [addEntry, typeResponse]);

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
      // Simulate amplitude if mic not available
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
      addEntry('ai', 'Speech recognition not supported in this browser. Please use text input.');
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
        processInput(text);
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

  useEffect(() => {
    return () => {
      stopAmplitudeTracking();
      recognitionRef.current?.stop();
    };
  }, [stopAmplitudeTracking]);

  return {
    status, isListening, transcript,
    aiResponse, commandHistory, amplitude,
    toggleMic, processInput,
  };
}
