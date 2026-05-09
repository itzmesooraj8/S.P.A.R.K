/**
 * AICore — Bottom-center intelligence copilot.
 * Features a glowing animated orb that expands to a terminal-style chat.
 * Uses /ws/ai streaming so tokens render live as they arrive.
 */
import { useState, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Bot, Send, X, Sparkles } from 'lucide-react';
import { useMonitorStore } from '@/store/useMonitorStore';
import { buildAuthedWsUrl } from '@/lib/wsAuth';
import { useTask } from '@/hooks/useTask';

const VERBOSE_WS = import.meta.env.VITE_VERBOSE_WS === 'true';
const wsWarn = (...a: unknown[]) => VERBOSE_WS && console.warn('[AICore WS]', ...a);
const wsErr = (...a: unknown[]) => VERBOSE_WS && console.error('[AICore WS]', ...a);

const RECONNECT_BASE_MS = 1200;
const RECONNECT_MAX_MS = 15000;

type AiFrame = {
  type?: string;
  token?: string;
  content?: string;
  message?: string;
};

export const AICore = () => {
  const aiCoreExpanded = useMonitorStore((s) => s.aiCoreExpanded);
  const toggleAICore = useMonitorStore((s) => s.toggleAICore);
  const aiMessages = useMonitorStore((s) => s.aiMessages);
  const addAIMessage = useMonitorStore((s) => s.addAIMessage);
  const { task, loading: taskLoading, runTask } = useTask();

  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [displayedResponse, setDisplayedResponse] = useState('');
  const [isSocketOnline, setIsSocketOnline] = useState(false);
  const [agentMode, setAgentMode] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const retryDelayRef = useRef(RECONNECT_BASE_MS);
  const outboundQueueRef = useRef<string[]>([]);
  const mountedRef = useRef(true);
  const awaitingResponseRef = useRef(false);
  const displayedResponseRef = useRef('');

  useEffect(() => {
    displayedResponseRef.current = displayedResponse;
  }, [displayedResponse]);

  const finalizeStream = useCallback((opts?: { errorText?: string }) => {
    awaitingResponseRef.current = false;
    setIsTyping(false);

    const final = displayedResponseRef.current.trim();
    displayedResponseRef.current = '';
    setDisplayedResponse('');

    if (final) addAIMessage('ai', final);
    if (opts?.errorText) addAIMessage('ai', opts.errorText);
  }, [addAIMessage]);

  const flushQueue = useCallback(() => {
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
      setIsSocketOnline(true);
      retryDelayRef.current = RECONNECT_BASE_MS;
      flushQueue();
    };

    ws.onmessage = (event) => {
      try {
        if (typeof event.data !== 'string') return;
        const frame = JSON.parse(event.data) as AiFrame;
        const frameType = (frame.type || '').toLowerCase();

        if (frameType === 'response_token' || frameType === 'token') {
          const token = (frame.token || frame.content || '');
          if (!token) return;
          setIsTyping(true);
          setDisplayedResponse((prev) => {
            const next = prev + token;
            displayedResponseRef.current = next;
            return next;
          });
          return;
        }

        if (frameType === 'response_done' || frameType === 'done') {
          finalizeStream();
          return;
        }

        if (frameType === 'error') {
          const message = (frame.message || frame.content || '').trim() || 'Unknown backend error';
          finalizeStream({ errorText: `[ERROR] ${message}` });
        }
      } catch (err) {
        wsErr('Failed to parse AI frame:', err);
      }
    };

    ws.onclose = (event) => {
      setIsSocketOnline(false);
      wsRef.current = null;

      if (awaitingResponseRef.current) {
        finalizeStream({ errorText: '[ERROR] Stream interrupted. Reconnecting...' });
      }

      if (!mountedRef.current) return;

      const baseDelay = Math.min(retryDelayRef.current, RECONNECT_MAX_MS);
      const jitter = Math.floor(Math.random() * 350);
      const delay = baseDelay + jitter;
      retryDelayRef.current = Math.min(Math.round(baseDelay * 1.7), RECONNECT_MAX_MS);

      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      wsWarn(`AICore socket closed (${event.code}). Reconnecting in ${Math.round(delay / 1000)}s...`);
      reconnectTimerRef.current = setTimeout(() => {
        reconnectTimerRef.current = null;
        connectWS();
      }, delay);
    };

    ws.onerror = (err) => {
      wsErr('AICore socket error:', err);
      ws.close();
    };
  }, [finalizeStream, flushQueue]);

  useEffect(() => {
    mountedRef.current = true;
    connectWS();

    return () => {
      mountedRef.current = false;
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      wsRef.current?.close(1000, 'component unmount');
    };
  }, [connectWS]);

  const handleSubmit = useCallback(() => {
    const query = input.trim();
    if (!query || isTyping || taskLoading) return;

    if (agentMode) {
      setInput('');
      setIsTyping(false);
      setDisplayedResponse('');
      displayedResponseRef.current = '';
      addAIMessage('user', query);
      void runTask(query);
      return;
    }

    setInput('');
    addAIMessage('user', query);
    setIsTyping(true);
    setDisplayedResponse('');
    displayedResponseRef.current = '';
    awaitingResponseRef.current = true;

    const payload = JSON.stringify({ message: query });
    const socket = wsRef.current;
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(payload);
      return;
    }

    outboundQueueRef.current.push(payload);
    addAIMessage('ai', '[SYSTEM] AI core reconnecting. Command queued...');
    connectWS();
  }, [addAIMessage, agentMode, connectWS, input, isTyping, runTask, taskLoading]);

  // Auto-scroll to bottom
  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: 'smooth',
    });
  }, [aiMessages, displayedResponse, isTyping]);

  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 flex flex-col items-center">
      {/* Expandable terminal */}
      <AnimatePresence>
        {aiCoreExpanded && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.92 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 16, scale: 0.92 }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            className="panel-hud w-[440px] max-w-[92vw] mb-3 overflow-hidden"
          >
            {/* Top accent line */}
            <div className="h-px w-full" style={{ background: 'linear-gradient(90deg, transparent, #00f5ff 40%, #00f5ff 60%, transparent)', opacity: 0.85 }} />
            {/* Corner brackets */}
            <span className="corner-tl" style={{ color: '#00f5ff' }} />
            <span className="corner-tr" style={{ color: '#00f5ff' }} />
            <span className="corner-bl" style={{ color: '#00f5ff', opacity: 0.4 }} />
            <span className="corner-br" style={{ color: '#00f5ff', opacity: 0.4 }} />

            {/* Header */}
            <div className="flex items-center justify-between px-4 py-2 border-b" style={{ borderColor: 'rgba(0,245,255,0.1)' }}>
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 rounded-sm flex items-center justify-center" style={{ background: '#00f5ff14', border: '1px solid #00f5ff30' }}>
                  <Sparkles size={10} style={{ color: '#00f5ff' }} />
                </div>
                <span className="text-[11px] font-bold tracking-[0.2em] font-mono" style={{ color: '#00f5ff', textShadow: '0 0 8px rgba(0,245,255,0.5)' }}>
                  AI CORE
                </span>
                <span className="text-[9px] font-mono text-foreground/25 tracking-widest">v2.4.1</span>
                <span className={`w-1 h-1 rounded-full ml-1 ${isSocketOnline ? 'bg-green-400 animate-pulse' : 'bg-amber-400'}`} />
              </div>
              <button
                onClick={toggleAICore}
                className="text-foreground/30 hover:text-foreground/70 transition-colors"
              >
                <X size={13} />
              </button>
            </div>

            {/* Message history */}
            <div
              ref={scrollRef}
              className="h-[220px] overflow-y-auto p-3 space-y-2 scrollbar-hud"
              style={{ background: 'rgba(0,0,0,0.2)' }}
            >
              {aiMessages.length === 0 && !isTyping && (
                <div className="text-[11px] text-foreground/40 leading-relaxed font-mono">
                  <span style={{ color: '#00f5ff80' }}>AI:</span>{' '}
                  Globe Monitor intelligence core active. Ask about any region,
                  conflict zone, market, or technology trend.
                </div>
              )}

              {aiMessages.map((msg, i) => (
                <div key={i} className="text-[11px] leading-relaxed font-mono">
                  {msg.role === 'user' ? (
                    <>
                      <span className="text-foreground/30 mr-1.5">›</span>
                      <span style={{ color: '#00f5ff' }}>{msg.content}</span>
                    </>
                  ) : (
                    <>
                      <span className="text-foreground/30 mr-1.5">AI:</span>
                      <span className="text-foreground/75">{msg.content}</span>
                    </>
                  )}
                </div>
              ))}

              {isTyping && (
                <div className="text-[11px] text-foreground/75 leading-relaxed font-mono">
                  <span className="text-foreground/30 mr-1.5">AI:</span>
                  {displayedResponse}
                  <span className="inline-block w-1.5 h-3 ml-0.5 animate-pulse" style={{ background: '#00f5ff' }} />
                </div>
              )}

              {task && (
                <div className="mt-2 rounded-md border p-3 text-[11px] font-mono" style={{ borderColor: 'rgba(0,245,255,0.18)', background: 'rgba(0,245,255,0.04)' }}>
                  <div className="font-semibold text-foreground/90">{task.goal}</div>
                  <div className="mt-1 text-foreground/50">
                    Status:{' '}
                    <span
                      className={task.status === 'done'
                        ? 'text-green-400'
                        : task.status === 'blocked'
                          ? 'text-red-400'
                          : 'text-amber-400'}
                    >
                      {task.status}
                    </span>
                  </div>
                  <ol className="mt-2 space-y-1 list-decimal list-inside text-foreground/75">
                    {task.steps.map((step, index) => (
                      <li key={`${step}-${index}`} className={index < task.results.length ? 'opacity-100' : 'opacity-50'}>
                        {step}
                        {task.results[index] && (
                          <span className="ml-2 text-foreground/45">→ {task.results[index].slice(0, 60)}</span>
                        )}
                      </li>
                    ))}
                  </ol>
                </div>
              )}
            </div>

            {/* Input bar */}
            <div className="px-3 py-2.5 border-t" style={{ borderColor: 'rgba(0,245,255,0.1)' }}>
              <div
                className="flex items-center gap-2 px-3 py-1.5 rounded-sm"
                style={{ background: 'rgba(0,245,255,0.04)', border: '1px solid rgba(0,245,255,0.15)' }}
              >
                <span className="font-mono text-xs" style={{ color: '#00f5ff80' }}>›</span>
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
                  placeholder={agentMode ? 'Enter a goal for the planner…' : 'Ask about any region or topic…'}
                  className="flex-1 bg-transparent text-[11px] text-foreground/80 placeholder:text-foreground/25 outline-none font-mono"
                  disabled={isTyping || taskLoading}
                />
                <button
                  type="button"
                  onClick={() => setAgentMode((value) => !value)}
                  className={`px-2 py-1 rounded text-[10px] font-mono border transition-colors ${agentMode
                    ? 'border-emerald-400/40 text-emerald-300 bg-emerald-400/10'
                    : 'border-white/10 text-foreground/45 hover:text-foreground/75'
                  }`}
                >
                  {agentMode ? 'AGENT' : 'CHAT'}
                </button>
                <button
                  onClick={handleSubmit}
                  disabled={isTyping || taskLoading || !input.trim()}
                  className="transition-colors disabled:opacity-30"
                  style={{ color: '#00f5ff' }}
                >
                  <Send size={12} />
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Glowing orb button */}
      <motion.button
        onClick={toggleAICore}
        className="relative w-12 h-12 rounded-full flex items-center justify-center"
        whileHover={{ scale: 1.12 }}
        whileTap={{ scale: 0.92 }}
      >
        {/* Outer glow ring */}
        <div
          className="absolute inset-0 rounded-full orb-pulse"
          style={{ background: 'rgba(0,245,255,0.15)' }}
        />
        {/* Inner glass surface */}
        <div
          className="absolute inset-1 rounded-full"
          style={{
            background: 'rgba(1, 9, 22, 0.85)',
            border: '1px solid rgba(0,245,255,0.35)',
            backdropFilter: 'blur(8px)',
          }}
        />
        {/* Bot icon */}
        <Bot size={18} className="relative z-10" style={{ color: '#00f5ff' }} />
        {/* Orbiting ring */}
        <motion.div
          className="absolute inset-0 rounded-full"
          animate={{ rotate: 360 }}
          transition={{ duration: 6, repeat: Infinity, ease: 'linear' }}
          style={{
            border: '1px dashed rgba(0,245,255,0.2)',
          }}
        />
      </motion.button>

      {/* Tooltip label */}
      <span className="mt-1 text-[8px] font-mono font-bold tracking-widest" style={{ color: 'rgba(0,245,255,0.4)' }}>
        AI CORE
      </span>
    </div>
  );
};
