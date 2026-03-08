/**
 * AICore — Bottom-center intelligence copilot.
 * Features a glowing animated orb that expands to a terminal-style chat.
 * Implements AGENTIC behavior: AI responses parse location keywords
 * and dispatch Zustand flyTo actions to manipulate the map.
 */
import { useState, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Bot, Send, X, Sparkles } from 'lucide-react';
import { useMonitorStore } from '@/store/useMonitorStore';
import { apiFetch } from '@/lib/api';

export const AICore = () => {
  const aiCoreExpanded = useMonitorStore((s) => s.aiCoreExpanded);
  const toggleAICore = useMonitorStore((s) => s.toggleAICore);
  const aiMessages = useMonitorStore((s) => s.aiMessages);
  const addAIMessage = useMonitorStore((s) => s.addAIMessage);
  const flyTo = useMonitorStore((s) => s.flyTo);

  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [displayedResponse, setDisplayedResponse] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);
  const intervalRef = useRef<number | null>(null);

  /** Typewriter animation for a completed text string */
  const typewriterEffect = useCallback((text: string, onDone: () => void) => {
    let i = 0;
    setDisplayedResponse('');
    intervalRef.current = window.setInterval(() => {
      if (i < text.length) {
        setDisplayedResponse(text.slice(0, i + 1));
        i++;
      } else {
        if (intervalRef.current) clearInterval(intervalRef.current);
        onDone();
      }
    }, 18);
  }, []);

  /** Submit user query to backend /api/commander/run */
  const handleSubmit = useCallback(async () => {
    if (!input.trim() || isTyping) return;

    const query = input.trim();
    setInput('');
    addAIMessage('user', query);
    setIsTyping(true);
    setDisplayedResponse('');

    try {
      const res = await apiFetch('/api/commander/run', {
        method: 'POST',
        body: JSON.stringify({ text: query }),
      });

      if (!res.ok) throw new Error(`${res.status}`);

      const data = await res.json();

      // Extract the reply text — adapt to your backend response shape
      const reply: string =
        data.reply ?? data.response ?? data.result ?? data.message ??
        (typeof data === 'string' ? data : JSON.stringify(data));

      // Extract optional coordinates for flyTo
      const lat = data.lat ?? data.latitude;
      const lng = data.lng ?? data.longitude;

      typewriterEffect(reply, () => {
        addAIMessage('ai', reply);
        setIsTyping(false);
        setDisplayedResponse('');
        if (lat != null && lng != null) {
          setTimeout(() => flyTo(lng, lat, 5), 500);
        }
      });
    } catch {
      const fallback = '⚠️ Backend unreachable — check that SPARK core is running on localhost:8000.';
      typewriterEffect(fallback, () => {
        addAIMessage('ai', fallback);
        setIsTyping(false);
        setDisplayedResponse('');
      });
    }
  }, [input, isTyping, addAIMessage, flyTo, typewriterEffect]);

  // Cleanup interval on unmount
  useEffect(() => {
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, []);

  // Auto-scroll to bottom
  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: 'smooth',
    });
  }, [aiMessages, displayedResponse]);

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
                <span className="w-1 h-1 rounded-full bg-green-400 animate-pulse ml-1" />
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

              {isTyping && displayedResponse && (
                <div className="text-[11px] text-foreground/75 leading-relaxed font-mono">
                  <span className="text-foreground/30 mr-1.5">AI:</span>
                  {displayedResponse}
                  <span className="inline-block w-1.5 h-3 ml-0.5 animate-pulse" style={{ background: '#00f5ff' }} />
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
                  placeholder="Ask about any region or topic…"
                  className="flex-1 bg-transparent text-[11px] text-foreground/80 placeholder:text-foreground/25 outline-none font-mono"
                  disabled={isTyping}
                />
                <button
                  onClick={handleSubmit}
                  disabled={isTyping || !input.trim()}
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
