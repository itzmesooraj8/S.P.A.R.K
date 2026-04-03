/**
 * CommandBar — Global SPARK command overlay
 * ─────────────────────────────────────────────────────────────────────────────
 * Triggered by Ctrl+Space (or programmatically via open prop).
 * Accepts natural-language commands, classifies intent in real-time,
 * and submits to /api/commander/run.
 *
 * Features:
 *   - Live intent preview badge as you type
 *   - Context snapshot auto-injected on submit
 *   - Command history (up/down arrow)
 *   - Inline loading / result states
 *   - Escape / click-outside to close
 */

import { useEffect, useRef, useState, KeyboardEvent } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Zap, ChevronRight, Loader2, CheckCircle, XCircle } from 'lucide-react';

interface Props {
  open: boolean;
  onClose: () => void;
  contextSnapshot?: Record<string, unknown>;
}

type IntentHint = 'CHAT' | 'TASK' | 'GLOBE_QUERY' | 'SYSTEM_QUERY' | 'CREATE_CASE' | 'RESEARCH' | 'CODE' | 'ROUTINE';

const INTENT_META: Record<IntentHint, { label: string; color: string }> = {
  CHAT:         { label: 'CHAT',    color: '#00f5ff' },
  TASK:         { label: 'TASK',    color: '#bf5af2' },
  GLOBE_QUERY:  { label: 'GLOBE',   color: '#30d158' },
  SYSTEM_QUERY: { label: 'SYSTEM',  color: '#ff9f0a' },
  CREATE_CASE:  { label: 'CASE',    color: '#ff453a' },
  RESEARCH:     { label: 'RSRCH',   color: '#64d2ff' },
  CODE:         { label: 'CODE',    color: '#ffd60a' },
  ROUTINE:      { label: 'ROUTINE', color: '#bf5af2' },
};

// Lightweight client-side heuristic for instant badge preview
function previewIntent(text: string): IntentHint {
  const tl = text.toLowerCase().trim();
  if (!tl) return 'CHAT';

  // ROUTINE: named operating modes
  if (/(dev mode|activate dev|start dev|developer mode|dev routine)/.test(tl)) return 'ROUTINE';
  if (/(monitor mode|globe monitor|threat monitor|activate monitor)/.test(tl)) return 'ROUTINE';
  if (/(focus mode|enable focus|crit only|focus session|activate focus)/.test(tl)) return 'ROUTINE';

  const taskVerbs = ['open ', 'launch ', 'start ', 'run ', 'execute ', 'go to ', 'navigate ', 'browse '];
  if (taskVerbs.some(v => tl.startsWith(v))) return 'TASK';

  const urlPat = /(?:https?:\/\/|www\.)[\w\-.]+\.[a-z]{2,}/;
  if (urlPat.test(tl)) return 'TASK';

  if (/(conflict|war|missile|crisis|invasion|breaking|geopolit|region|sanction)/.test(tl)) return 'GLOBE_QUERY';
  if (/(cpu|ram|memory|uptime|ping|gpu|status|health|metric|performance)/.test(tl)) return 'SYSTEM_QUERY';
  if (/(create case|new case|report|escalate|log case)/.test(tl)) return 'CREATE_CASE';
  if (/(code|debug|refactor|function|class|script|python|typescript|write a|fix this)/.test(tl)) return 'CODE';
  if (/(research|find|search|look up|what is|explain|summarize|who is|where is)/.test(tl)) return 'RESEARCH';

  return 'CHAT';
}

/** Maps a user command to a routine key (dev | monitor | focus), or null. */
function detectRoutine(text: string): string | null {
  const tl = text.toLowerCase().trim();
  if (/(dev mode|activate dev|start dev|developer mode|dev routine)/.test(tl)) return 'dev';
  if (/(monitor mode|globe monitor|threat monitor|activate monitor)/.test(tl)) return 'monitor';
  if (/(focus mode|enable focus|crit only|focus session|activate focus)/.test(tl)) return 'focus';
  return null;
}

const BACKEND_PORT = import.meta.env.VITE_BACKEND_PORT ?? '8000';
const BASE_URL = `${window.location.protocol}//${window.location.hostname}:${BACKEND_PORT}`;

const HISTORY_MAX = 20;

type SubmitState = 'idle' | 'loading' | 'done' | 'error';

export default function CommandBar({ open, onClose, contextSnapshot }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const overlayRef = useRef<HTMLDivElement>(null);

  const [value, setValue] = useState('');
  const [intentHint, setIntentHint] = useState<IntentHint>('CHAT');
  const [submitState, setSubmitState] = useState<SubmitState>('idle');
  const [resultText, setResultText] = useState<string>('');
  const [cmdHistory, setCmdHistory] = useState<string[]>([]);
  const [histIdx, setHistIdx] = useState(-1);

  // Focus on open
  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 50);
      setSubmitState('idle');
      setResultText('');
    }
  }, [open]);

  // Update intent badge as user types
  useEffect(() => {
    setIntentHint(previewIntent(value));
    setHistIdx(-1);
  }, [value]);

  // Click outside to close
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (overlayRef.current && !overlayRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    if (open) document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open, onClose]);

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Escape') { onClose(); return; }
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit(); return; }

    // History navigation
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      const next = Math.min(histIdx + 1, cmdHistory.length - 1);
      setHistIdx(next);
      if (cmdHistory[next]) setValue(cmdHistory[next]);
    }
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      const next = Math.max(histIdx - 1, -1);
      setHistIdx(next);
      setValue(next === -1 ? '' : cmdHistory[next]);
    }
  };

  const submit = async () => {
    const text = value.trim();
    if (!text || submitState === 'loading') return;

    // Add to history
    setCmdHistory(prev => [text, ...prev.filter(c => c !== text)].slice(0, HISTORY_MAX));

    setSubmitState('loading');
    setResultText('');

    try {
      // Detect routine commands and route directly to the routine endpoint
      const routineName = detectRoutine(text);
      let url: string;
      let body: string;

      if (routineName) {
        url  = `${BASE_URL}/api/commander/routine/${routineName}`;
        body = JSON.stringify({});
      } else {
        url  = `${BASE_URL}/api/commander/run`;
        body = JSON.stringify({ text, context_snapshot: contextSnapshot ?? {} });
      }

      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body,
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setResultText(data.result ?? (routineName ? `${data.name ?? routineName} activated.` : 'Done.'));
      setSubmitState('done');
      setValue('');

      // Close after a short display window for non-TASK/non-ROUTINE intents
      const intent = data.intent as IntentHint;
      const autoCloseMs = (intent === 'TASK' || routineName) ? 1500 : 3000;
      setTimeout(onClose, autoCloseMs);
    } catch (err) {
      setResultText(`Error: ${err instanceof Error ? err.message : String(err)}`);
      setSubmitState('error');
    }
  };

  const meta = INTENT_META[intentHint];

  const suggestions = [
    // ― Routines ―
    'dev mode',
    'monitor mode',
    'focus mode',
    // ― Quick tasks ―
    'open vscode',
    'open chrome',
    'run ipconfig',
    // ― Intelligence ―
    'what is the CPU load?',
    'latest conflict briefing',
    'create case: network anomaly',
  ];

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-[100] flex items-start justify-center pt-[18vh]"
          style={{ background: 'rgba(0,2,20,0.65)', backdropFilter: 'blur(6px)' }}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.12 }}
        >
          <motion.div
            ref={overlayRef}
            className="w-full max-w-2xl mx-4"
            initial={{ y: -20, opacity: 0, scale: 0.97 }}
            animate={{ y: 0, opacity: 1, scale: 1 }}
            exit={{ y: -16, opacity: 0, scale: 0.97 }}
            transition={{ type: 'spring', damping: 22, stiffness: 300 }}
          >
            {/* Main bar */}
            <div
              className="rounded-xl overflow-hidden"
              style={{
                background: 'rgba(0,4,28,0.96)',
                border: `1px solid ${meta.color}60`,
                boxShadow: `0 0 40px ${meta.color}20, 0 8px 40px rgba(0,0,0,0.6)`,
              }}
            >
              {/* Input row */}
              <div className="flex items-center gap-3 px-4 py-3 relative">
                {/* SPARK glyph */}
                <Zap
                  size={16}
                  className="shrink-0 transition-colors duration-200"
                  style={{ color: meta.color }}
                />

                {/* Input */}
                <input
                  ref={inputRef}
                  type="text"
                  value={value}
                  onChange={(e) => setValue(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask SPARK anything…"
                  disabled={submitState === 'loading'}
                  className="flex-1 bg-transparent outline-none font-orbitron text-sm text-white/90 placeholder:text-white/25 tracking-wide"
                  spellCheck={false}
                  autoComplete="off"
                />

                {/* Intent badge */}
                {value && submitState === 'idle' && (
                  <span
                    className="font-orbitron text-[8px] px-2 py-0.5 rounded shrink-0 transition-all duration-150"
                    style={{
                      background: `${meta.color}20`,
                      color: meta.color,
                      border: `1px solid ${meta.color}50`,
                    }}
                  >
                    {meta.label}
                  </span>
                )}

                {/* Submit state */}
                {submitState === 'loading' && (
                  <Loader2 size={14} className="text-hud-cyan animate-spin shrink-0" />
                )}
                {submitState === 'done' && (
                  <CheckCircle size={14} className="text-green-400 shrink-0" />
                )}
                {submitState === 'error' && (
                  <XCircle size={14} className="text-red-400 shrink-0" />
                )}

                {/* Enter hint */}
                {value && submitState === 'idle' && (
                  <div className="flex items-center gap-1 shrink-0">
                    <span className="font-orbitron text-[7px] text-white/20 border border-white/15 rounded px-1 py-px">↵</span>
                  </div>
                )}
              </div>

              {/* Scan-line accent */}
              <div
                className="h-px w-full"
                style={{ background: `linear-gradient(90deg, transparent, ${meta.color}60, transparent)` }}
              />

              {/* Result / suggestions */}
              {(resultText || (!value && submitState === 'idle')) && (
                <div className="px-4 py-2.5">
                  {resultText ? (
                    <p
                      className="font-mono-tech text-[10px] leading-relaxed"
                      style={{ color: submitState === 'error' ? '#ff453a' : '#30d158' }}
                    >
                      {resultText}
                    </p>
                  ) : (
                    <div className="flex flex-wrap gap-1.5">
                      {suggestions.map((s) => (
                        <button
                          key={s}
                          onClick={() => { setValue(s); inputRef.current?.focus(); }}
                          className="flex items-center gap-1 font-mono-tech text-[8px] text-white/35 hover:text-hud-cyan/70 transition-colors"
                        >
                          <ChevronRight size={8} />
                          {s}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Footer hint */}
            <div className="flex justify-center mt-2 gap-4">
              <span className="font-orbitron text-[7px] text-white/20">↑↓ history</span>
              <span className="font-orbitron text-[7px] text-white/20">↵ execute</span>
              <span className="font-orbitron text-[7px] text-white/20">Esc close</span>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
