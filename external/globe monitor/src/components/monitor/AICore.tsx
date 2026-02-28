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

// ========== MOCK AI RESPONSE DATABASE ==========
const AI_RESPONSES: Record<string, { text: string; lat?: number; lng?: number }> = {
  'black sea': {
    text: '🔴 ALERT: Black Sea region shows elevated naval activity. NATO maritime patrols increased 40% this quarter. Russian Black Sea Fleet conducting exercises near Sevastopol. Monitoring 3 active conflict vectors.',
    lat: 44.0,
    lng: 34.0,
  },
  ukraine: {
    text: '⚠️ Ukraine situation: Front line activity concentrated in Zaporizhzhia and Donetsk oblasts. Satellite imagery confirms infrastructure damage in 12 locations. Humanitarian corridors intermittently operational. Risk level: CRITICAL.',
    lat: 48.38,
    lng: 31.17,
  },
  taiwan: {
    text: '🟡 Taiwan Strait: PLA naval exercises detected in eastern approaches. USINDOPACOM assets repositioned. Semiconductor supply chain risk elevated to AMBER. TSMC production unaffected.',
    lat: 24.0,
    lng: 121.0,
  },
  gaza: {
    text: '🔴 CRITICAL: Gaza humanitarian crisis at Level 5. Active conflict in northern and central sectors. Medical infrastructure at 15% capacity. 4 active ceasefire negotiation tracks being monitored.',
    lat: 31.35,
    lng: 34.31,
  },
  market: {
    text: '📊 Global Market Summary: Risk-off sentiment dominant. VIX elevated at 28.5. Safe haven flows into USD, Gold, CHF. EM currencies under pressure. BTC showing decorrelation at 0.42.',
  },
  ai: {
    text: '💻 AI Development Tracker: 3 new foundation models this week. Global compute demand up 200% YoY. Regulatory proposals active in EU, US, CN. OpenAI cluster utilization at peak.',
    lat: 37.77,
    lng: -122.42,
  },
  crypto: {
    text: '🪙 Crypto Intelligence: BTC whale accumulation phase detected. On-chain metrics show 73% of supply unmoved 6+ months. ETH staking ratio at all-time high. DeFi TVL recovering.',
    lat: 47.37,
    lng: 8.54,
  },
  sudan: {
    text: '🔴 Sudan Crisis: RSF forces advancing on Khartoum from three vectors. Civilian displacement exceeds 8M. International intervention calls escalating. Humanitarian access severely restricted.',
    lat: 15.6,
    lng: 32.5,
  },
  default: {
    text: '🌐 World Monitor V2 online. All systems nominal. Tracking 847 active events across 4 domains. Global threat level: ELEVATED. Type a region, country, or topic for detailed analysis.',
  },
};

/** Match user input to an AI response */
const findResponse = (input: string) => {
  const lower = input.toLowerCase();
  for (const [key, resp] of Object.entries(AI_RESPONSES)) {
    if (key !== 'default' && lower.includes(key)) return resp;
  }
  return AI_RESPONSES.default;
};

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

  /** Submit user query and generate mock AI response with typewriter effect */
  const handleSubmit = useCallback(() => {
    if (!input.trim() || isTyping) return;

    const query = input.trim();
    setInput('');
    addAIMessage('user', query);

    const response = findResponse(query);
    setIsTyping(true);
    setDisplayedResponse('');

    let i = 0;
    intervalRef.current = window.setInterval(() => {
      if (i < response.text.length) {
        setDisplayedResponse(response.text.slice(0, i + 1));
        i++;
      } else {
        if (intervalRef.current) clearInterval(intervalRef.current);
        addAIMessage('ai', response.text);
        setIsTyping(false);
        setDisplayedResponse('');

        // Agentic: fly to location if response has coordinates
        if (response.lat != null && response.lng != null) {
          setTimeout(() => flyTo(response.lng!, response.lat!, 5), 500);
        }
      }
    }, 18);
  }, [input, isTyping, addAIMessage, flyTo]);

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
            initial={{ opacity: 0, y: 20, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.9 }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            className="glass-panel-strong rounded-2xl w-[440px] max-w-[92vw] mb-3 overflow-hidden"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-2.5 border-b border-border/30">
              <div className="flex items-center gap-2">
                <Sparkles size={14} className="text-primary" />
                <span className="text-[11px] font-mono tracking-widest text-primary font-semibold">
                  AI CORE
                </span>
                <span className="text-[9px] font-mono text-muted-foreground">
                  v2.4.1
                </span>
              </div>
              <button
                onClick={toggleAICore}
                className="text-muted-foreground hover:text-foreground transition-colors"
              >
                <X size={14} />
              </button>
            </div>

            {/* Message history */}
            <div
              ref={scrollRef}
              className="h-[260px] overflow-y-auto p-3 space-y-2.5"
            >
              {/* Welcome message */}
              {aiMessages.length === 0 && !isTyping && (
                <div className="text-xs text-muted-foreground leading-relaxed font-mono">
                  <span className="text-primary">AI:</span> World Monitor V2
                  intelligence core active. Ask about any region, conflict zone,
                  market, or technology trend for real-time analysis.
                </div>
              )}

              {aiMessages.map((msg, i) => (
                <div
                  key={i}
                  className={`text-xs leading-relaxed ${
                    msg.role === 'user'
                      ? 'text-primary font-mono'
                      : 'text-foreground/80'
                  }`}
                >
                  <span className="text-[10px] text-muted-foreground font-mono mr-1.5">
                    {msg.role === 'user' ? '>' : 'AI:'}
                  </span>
                  {msg.content}
                </div>
              ))}

              {/* Typewriter effect for current response */}
              {isTyping && displayedResponse && (
                <div className="text-xs text-foreground/80 leading-relaxed">
                  <span className="text-[10px] text-muted-foreground font-mono mr-1.5">
                    AI:
                  </span>
                  {displayedResponse}
                  <span className="inline-block w-1.5 h-3.5 bg-primary ml-0.5 animate-pulse" />
                </div>
              )}
            </div>

            {/* Input */}
            <div className="p-3 border-t border-border/30">
              <div className="flex items-center gap-2 bg-background/60 rounded-lg px-3 py-2 border border-border/30">
                <span className="text-primary font-mono text-xs">{'>'}</span>
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
                  placeholder="Ask about any region or topic..."
                  className="flex-1 bg-transparent text-xs text-foreground placeholder:text-muted-foreground outline-none font-mono"
                  disabled={isTyping}
                />
                <button
                  onClick={handleSubmit}
                  disabled={isTyping || !input.trim()}
                  className="text-primary hover:text-primary/80 transition-colors disabled:opacity-40"
                >
                  <Send size={14} />
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Glowing orb button */}
      <motion.button
        onClick={toggleAICore}
        className="relative w-14 h-14 rounded-full flex items-center justify-center"
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.95 }}
      >
        {/* Outer glow */}
        <div className="absolute inset-0 rounded-full bg-primary/20 orb-pulse" />
        {/* Inner ring */}
        <div className="absolute inset-1 rounded-full bg-primary/10 backdrop-blur-sm" />
        {/* Core */}
        <div className="absolute inset-2 rounded-full bg-background/80 border border-primary/30 flex items-center justify-center">
          <Bot size={20} className="text-primary" />
        </div>
        {/* Orbiting particle */}
        <motion.div
          className="absolute w-1.5 h-1.5 rounded-full bg-primary"
          animate={{ rotate: 360 }}
          transition={{ duration: 4, repeat: Infinity, ease: 'linear' }}
          style={{ top: 0, left: '50%', transformOrigin: '0 28px' }}
        />
      </motion.button>
    </div>
  );
};
