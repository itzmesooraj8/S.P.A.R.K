import { useEffect, useRef, useState, KeyboardEvent } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Zap, ChevronRight, Loader2, Mic } from 'lucide-react';
import { useCommandBarStore } from '@/store/commandBarStore';
import VoiceWaveform from './VoiceWaveform';

type IntentHint = 'CHAT' | 'TASK' | 'GLOBE' | 'SYSTEM' | 'CASE' | 'RSRCH' | 'CODE' | 'ROUTINE';

export default function CommandDock() {
  const { isOpen, setOpen } = useCommandBarStore();
  const inputRef = useRef<HTMLInputElement>(null);
  const [value, setValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 100);
      setValue('');
    }
  }, [isOpen]);

  useEffect(() => {
    const handleKeyDown = (e: globalThis.KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [setOpen]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!value.trim()) return;
    // Dispatch command
    window.dispatchEvent(new CustomEvent('module-activate', { 
      detail: { module: 'agent', params: { query: value } } 
    }));
    setValue('');
    setOpen(false);
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ y: 100, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: 100, opacity: 0 }}
          transition={{ type: 'spring', stiffness: 300, damping: 25 }}
          className="fixed bottom-8 left-1/2 -translate-x-1/2 z-[100] w-full max-w-2xl px-4"
        >
          <div className="relative group">
            {/* Ambient Glow */}
            <div className="absolute -inset-2 bg-[#00E5FF] opacity-10 blur-xl rounded-full transition-opacity group-hover:opacity-20" />
            
            {/* Dock Container */}
            <div className="relative bg-[#020617]/80 backdrop-blur-xl border border-[#00E5FF]/20 rounded-2xl shadow-[0_0_30px_rgba(0,229,255,0.1),inset_0_0_20px_rgba(255,255,255,0.02)] overflow-hidden">
              
              <form onSubmit={handleSubmit} className="flex items-center px-6 py-4">
                <span className="font-space text-[#00E5FF] font-bold text-lg mr-3 animate-pulse">&gt;</span>
                
                <input
                  ref={inputRef}
                  type="text"
                  value={value}
                  onChange={(e) => {
                    setValue(e.target.value);
                    setIsTyping(true);
                    setTimeout(() => setIsTyping(false), 500);
                  }}
                  className="flex-1 bg-transparent border-none outline-none font-inter text-white/90 text-lg placeholder:text-white/20"
                  placeholder="spark await command..."
                  spellCheck={false}
                />
                
                {/* Simulated Voice Waveform when typing */}
                <div className="w-16 h-8 opacity-50 overflow-hidden flex items-center">
                  {isTyping ? (
                    <VoiceWaveform amplitude={[0.5, 0.8, 0.3, 0.9, 0.4]} width={64} height={20} barWidth={2} gap={2} />
                  ) : (
                    <Mic size={18} className="text-[#00E5FF]/40 ml-auto" />
                  )}
                </div>
              </form>

              {/* Suggestions / Predictions */}
              <motion.div 
                initial={false}
                animate={{ height: value ? 'auto' : 0, opacity: value ? 1 : 0 }}
                className="px-6 pb-4 flex gap-2 flex-wrap"
              >
                {['analyze network', 'initiate override', 'system diagnostics'].map(s => (
                  <button 
                    key={s}
                    type="button"
                    onClick={() => setValue(s)}
                    className="font-mono-tech text-[10px] uppercase text-white/40 hover:text-[#00E5FF] border border-white/10 hover:border-[#00E5FF]/50 rounded px-2 py-1 transition-all"
                  >
                    {s}
                  </button>
                ))}
              </motion.div>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
