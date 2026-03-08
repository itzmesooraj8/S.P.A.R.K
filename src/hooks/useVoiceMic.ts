import { useState, useCallback, useRef, useEffect } from 'react';

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000';

// Silence detection parameters
const SILENCE_THRESHOLD = 0.02;  // RMS amplitude threshold for silence
const SILENCE_DURATION_MS = 1500;  // 1.5 seconds to trigger auto-submit

export interface MicState {
  isRecording: boolean;
  isTranscribing: boolean;
  transcript: string;
  error: string | null;
}

/**
 * Hook for capturing microphone audio and transcribing via /api/voice/transcribe
 * 
 * Supports:
 *   - Manual recording control (startRecording, stopRecording)
 *   - Auto-submit after 1.5s of silence (when onAutoSubmit callback provided)
 *   - Real-time silence detection via Web Audio API
 * 
 * Usage:
 *   const { isRecording, transcript, startRecording, stopRecording } = useVoiceMic({
 *     onAutoSubmit: (text) => console.log('Command:', text)
 *   });
 */
export function useVoiceMic(options?: { onAutoSubmit?: (transcript: string) => void }) {
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [error, setError] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const silenceTimerRef = useRef<number | null>(null);
  const lastAudioLevelRef = useRef<number>(0);
  const audioContextRef = useRef<AudioContext | null>(null);

  const startRecording = useCallback(async () => {
    try {
      setError(null);
      setTranscript('');

      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      streamRef.current = stream;
      audioChunksRef.current = [];

      // Set up Web Audio API for silence detection
      if (!audioContextRef.current) {
        type WebkitWindow = Window & { webkitAudioContext?: typeof AudioContext };
        const AudioCtx = window.AudioContext || (window as WebkitWindow).webkitAudioContext;
        audioContextRef.current = new AudioCtx!();
      }
      const audioContext = audioContextRef.current;
      
      const source = audioContext.createMediaStreamSource(stream);
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 2048;
      source.connect(analyser);
      analyserRef.current = analyser;

      // Create MediaRecorder with audio/webm codec (most compatible)
      const mimeType = MediaRecorder.isTypeSupported('audio/webm')
        ? 'audio/webm'
        : 'audio/mp4';

      const mediaRecorder = new MediaRecorder(stream, {
        mimeType,
        audioBitsPerSecond: 128000,
      });

      mediaRecorder.ondataavailable = (event) => {
        audioChunksRef.current.push(event.data);
      };

      mediaRecorder.onerror = (event) => {
        console.error('MediaRecorder error:', event.error);
        setError(`Recording error: ${event.error}`);
      };

      mediaRecorderRef.current = mediaRecorder;
      mediaRecorder.start();
      setIsRecording(true);

      // Start silence detection loop
      _startSilenceDetection();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to access microphone';
      setError(message);
      console.error('Mic access error:', err);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const stopRecording = useCallback(async (autoSubmit = false): Promise<string> => {
    return new Promise((resolve, reject) => {
      const mediaRecorder = mediaRecorderRef.current;
      if (!mediaRecorder || !streamRef.current) {
        reject(new Error('Recording not started'));
        return;
      }

      // Clear silence timer
      if (silenceTimerRef.current) {
        clearTimeout(silenceTimerRef.current);
        silenceTimerRef.current = null;
      }

      mediaRecorder.onstop = async () => {
        // Stop all tracks to clean up
        streamRef.current?.getTracks().forEach(track => track.stop());
        streamRef.current = null;
        setIsRecording(false);

        // Combine audio chunks into a single blob
        const audioBlob = new Blob(audioChunksRef.current, {
          type: mediaRecorder.mimeType,
        });
        audioChunksRef.current = [];

        if (audioBlob.size === 0) {
          reject(new Error('No audio recorded'));
          return;
        }

        // Send to backend for transcription
        setIsTranscribing(true);
        try {
          const formData = new FormData();
          formData.append('file', audioBlob, `recording.${audioBlob.type.split('/')[1]}`);
          formData.append('language', 'en');

          const response = await fetch(`${API_BASE}/api/voice/transcribe`, {
            method: 'POST',
            body: formData,
          });

          if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
          }

          const data = await response.json();
          if (data.success && data.text) {
            setTranscript(data.text);
            
            // If auto-submit (from silence detection), call the callback
            if (autoSubmit && options?.onAutoSubmit) {
              console.log('🎤 Auto-submitting transcript from silence detection');
              options.onAutoSubmit(data.text);
            }
            
            resolve(data.text);
          } else {
            throw new Error(data.error || 'Transcription failed');
          }
        } catch (err) {
          const message = err instanceof Error ? err.message : 'Transcription error';
          setError(message);
          console.error('Transcription error:', err);
          reject(err);
        } finally {
          setIsTranscribing(false);
        }
      };

      mediaRecorder.stop();
    });
  }, [options]);

  // Silence detection loop — monitors audio levels and auto-stops after 1.5s of quiet
  const _startSilenceDetection = () => {
    if (!analyserRef.current) return;

    let consecutiveSilenceTime = 0;
    const analyser = analyserRef.current;
    const dataArray = new Uint8Array(analyser.frequencyBinCount);

    const detectSilence = () => {
      analyser.getByteFrequencyData(dataArray);

      // Calculate RMS (root mean square) of the frequency data
      let sum = 0;
      for (let i = 0; i < dataArray.length; i++) {
        sum += dataArray[i] * dataArray[i];
      }
      const rms = Math.sqrt(sum / dataArray.length) / 255;  // Normalize to 0-1
      lastAudioLevelRef.current = rms;

      // Check if below silence threshold
      if (rms < SILENCE_THRESHOLD) {
        consecutiveSilenceTime += 100;
        if (consecutiveSilenceTime >= SILENCE_DURATION_MS && isRecording) {
          console.log('🎤 Silence detected — auto-stopping recording');
          stopRecording(true).catch((err) => {
            console.error('Auto-stop error:', err);
            setError('Failed to auto-submit transcript');
          });
          return;
        }
      } else {
        consecutiveSilenceTime = 0;
      }

      // Continue detecting
      if (isRecording) {
        silenceTimerRef.current = window.setTimeout(detectSilence, 100);
      }
    };

    detectSilence();
  };

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const reset = useCallback(() => {
    setTranscript('');
    setError(null);
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }
    if (isRecording) {
      mediaRecorderRef.current?.stop();
    }
  }, [isRecording]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (silenceTimerRef.current) {
        clearTimeout(silenceTimerRef.current);
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
    };
  }, []);

  return {
    isRecording,
    isTranscribing,
    transcript,
    error,
    startRecording,
    stopRecording,
    clearError,
    reset,
  };
}
