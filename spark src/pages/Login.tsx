import { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Shield, Key, Eye, EyeOff, Zap, Network, Cpu, Activity } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';

export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, isAuthenticated, error, clearError } = useAuth();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPw, setShowPw] = useState(false);
  const [isSubmitting, setSubmitting] = useState(false);

  // Redirect if already authed
  useEffect(() => {
    if (isAuthenticated) {
      const from = (location.state as { from?: string })?.from ?? '/';
      navigate(from, { replace: true });
    }
  }, [isAuthenticated, navigate, location]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) return;
    clearError();
    setSubmitting(true);
    
    // Artificial delay for cinematic feel
    await new Promise(r => setTimeout(r, 1200));
    
    const ok = await login(username.trim(), password);
    setSubmitting(false);
    if (ok) {
      const from = (location.state as { from?: string })?.from ?? '/';
      navigate(from, { replace: true });
    }
  };

  // Shared spring transition
  const springTransition = { type: "spring", stiffness: 120, damping: 18 };

  return (
    <div className="relative w-full h-screen overflow-hidden bg-[#020617] text-white selection:bg-[#00E5FF]/30">
      
      {/* ========================================================= */}
      {/* LAYER 1: Background Atmosphere                            */}
      {/* ========================================================= */}
      <div 
        className="absolute inset-0 pointer-events-none"
        style={{
          background: 'radial-gradient(circle at 20% 50%, rgba(0, 80, 120, 0.15), transparent 60%), radial-gradient(circle at 80% 80%, rgba(0, 229, 255, 0.05), transparent 50%), linear-gradient(180deg, #020617 0%, #010308 100%)'
        }}
      />

      {/* ========================================================= */}
      {/* LAYER 2: Tactical Grid                                    */}
      {/* ========================================================= */}
      <motion.div 
        className="absolute inset-0 pointer-events-none opacity-5"
        animate={{ backgroundPosition: ['0px 0px', '0px 80px'] }}
        transition={{ duration: 10, repeat: Infinity, ease: 'linear' }}
        style={{
          backgroundImage: 'linear-gradient(rgba(255,255,255,1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,1) 1px, transparent 1px)',
          backgroundSize: '80px 80px'
        }}
      />

      {/* ========================================================= */}
      {/* LAYER 3: Floating HUD Particles / Scans                   */}
      {/* ========================================================= */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        {/* Subtle Scan Streaks */}
        <motion.div 
          animate={{ y: ['-100vh', '100vh'] }}
          transition={{ duration: 8, repeat: Infinity, ease: 'linear', delay: 2 }}
          className="absolute left-[15%] w-[1px] h-[30vh] bg-gradient-to-b from-transparent via-[#00E5FF]/20 to-transparent"
        />
        <motion.div 
          animate={{ y: ['-100vh', '100vh'] }}
          transition={{ duration: 12, repeat: Infinity, ease: 'linear', delay: 5 }}
          className="absolute right-[25%] w-[1px] h-[20vh] bg-gradient-to-b from-transparent via-[#00E5FF]/10 to-transparent"
        />
      </div>

      {/* ========================================================= */}
      {/* LAYER 4: Main Interface Grid                              */}
      {/* ========================================================= */}
      <div className="relative z-10 w-full h-full max-w-[1400px] mx-auto px-12 grid grid-cols-[1.2fr_0.8fr] gap-16 items-center">
        
        {/* LEFT PANEL: AI INTRODUCTION */}
        <div className="flex flex-col justify-center pr-8">
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ ...springTransition, delay: 0.2 }}
          >
            <div className="flex items-center gap-4 mb-6">
              <div className="w-12 h-12 flex items-center justify-center border border-[#00E5FF]/30 rounded-lg bg-[#00E5FF]/5 shadow-[0_0_20px_rgba(0,229,255,0.1)]">
                <Zap className="text-[#00E5FF]" size={24} />
              </div>
              <div className="font-orbitron text-4xl font-black tracking-[0.25em] text-white drop-shadow-[0_0_15px_rgba(255,255,255,0.2)]">
                S.P.A.R.K
              </div>
            </div>
            
            <h2 className="font-space text-2xl text-[#00E5FF]/90 font-medium mb-4 tracking-wide">
              Sovereign Processing & Autonomous Response Kernel
            </h2>
            
            <p className="font-inter text-base text-slate-400 leading-relaxed max-w-xl mb-12">
              Adaptive Artificial Intelligence Infrastructure. Initiating handshake protocol and verifying cryptographic identity. Unauthorized access is strictly logged and actively repelled.
            </p>

            {/* Monitoring Nodes */}
            <div className="grid grid-cols-2 gap-4 max-w-lg">
              {[
                { icon: Cpu, label: 'Neural Systems', status: 'NOMINAL' },
                { icon: Network, label: 'Global Nodes', status: 'SYNCED' },
                { icon: Shield, label: 'Threat Channels', status: 'SECURE' },
                { icon: Activity, label: 'Quantum Telemetry', status: 'ACTIVE' },
              ].map((item, idx) => (
                <motion.div 
                  key={idx}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ ...springTransition, delay: 0.5 + idx * 0.1 }}
                  className="flex items-center gap-3 p-3 rounded bg-white/[0.02] border border-white/[0.05]"
                >
                  <item.icon size={16} className="text-[#00E5FF]/60" />
                  <div className="flex flex-col">
                    <span className="font-inter text-xs text-slate-300">{item.label}</span>
                    <span className="font-mono-tech text-[10px] text-[#00E5FF]/80 tracking-widest mt-0.5">{item.status}</span>
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.div>
        </div>

        {/* RIGHT PANEL: AUTH MODULE */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          transition={{ ...springTransition, delay: 0.4 }}
          className="relative"
        >
          {/* Subtle Backglow */}
          <div className="absolute -inset-1 bg-gradient-to-br from-[#00E5FF]/20 to-transparent blur-2xl opacity-30 rounded-3xl" />
          
          <div className="relative bg-[#050f19]/60 backdrop-blur-xl border border-[#00E5FF]/10 rounded-2xl p-10 shadow-[0_0_40px_rgba(0,0,0,0.5),inset_0_0_20px_rgba(255,255,255,0.02)]">
            
            {/* Header */}
            <div className="flex items-center justify-between mb-8 pb-4 border-b border-white/[0.05]">
              <div className="font-orbitron text-sm tracking-[0.25em] text-white/90">
                SOVEREIGN ACCESS
              </div>
              <div className="font-mono-tech text-[10px] text-[#00E5FF]/60 bg-[#00E5FF]/10 px-2 py-1 rounded border border-[#00E5FF]/20">
                SECURE PORT
              </div>
            </div>

            <form onSubmit={handleSubmit} className="space-y-6">
              
              {/* Operator ID */}
              <div className="space-y-2">
                <label className="font-mono-tech text-[11px] text-slate-400 uppercase tracking-widest flex items-center gap-2">
                  <span>Operator ID</span>
                </label>
                <input
                  type="text"
                  value={username}
                  onChange={e => { setUsername(e.target.value); clearError(); }}
                  disabled={isSubmitting}
                  placeholder="Enter designation"
                  className="w-full bg-white/[0.02] border border-[#00E5FF]/15 rounded h-14 px-[18px] font-mono-tech text-sm text-[#00E5FF] placeholder:text-slate-600 outline-none transition-all focus:bg-[#00E5FF]/[0.02] disabled:opacity-50"
                  style={{
                    backdropFilter: 'blur(12px)',
                    boxShadow: 'none'
                  }}
                  onFocus={(e) => {
                    e.target.style.boxShadow = '0 0 0 1px #00e5ff, 0 0 30px rgba(0,229,255,0.15)';
                    e.target.style.borderColor = '#00e5ff';
                  }}
                  onBlur={(e) => {
                    e.target.style.boxShadow = 'none';
                    e.target.style.borderColor = 'rgba(0,255,255,0.15)';
                  }}
                />
              </div>

              {/* Encryption Key */}
              <div className="space-y-2">
                <label className="font-mono-tech text-[11px] text-slate-400 uppercase tracking-widest flex items-center gap-2">
                  <span>Encryption Key</span>
                </label>
                <div className="relative">
                  <input
                    type={showPw ? 'text' : 'password'}
                    value={password}
                    onChange={e => { setPassword(e.target.value); clearError(); }}
                    disabled={isSubmitting}
                    placeholder="••••••••"
                    className="w-full bg-white/[0.02] border border-[#00E5FF]/15 rounded h-14 px-[18px] font-mono-tech text-sm text-[#00E5FF] placeholder:text-slate-600 outline-none transition-all focus:bg-[#00E5FF]/[0.02] disabled:opacity-50"
                    style={{
                      backdropFilter: 'blur(12px)',
                      boxShadow: 'none'
                    }}
                    onFocus={(e) => {
                      e.target.style.boxShadow = '0 0 0 1px #00e5ff, 0 0 30px rgba(0,229,255,0.15)';
                      e.target.style.borderColor = '#00e5ff';
                    }}
                    onBlur={(e) => {
                      e.target.style.boxShadow = 'none';
                      e.target.style.borderColor = 'rgba(0,255,255,0.15)';
                    }}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPw(v => !v)}
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500 hover:text-[#00E5FF] transition-colors"
                  >
                    {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              {/* Threat Level */}
              <div className="flex items-center gap-2 pt-2">
                <Shield size={12} className="text-[#30d158]" />
                <span className="font-mono-tech text-[10px] text-slate-400 tracking-widest">
                  Threat Level: <span className="text-[#30d158]">SECURE</span>
                </span>
              </div>

              {/* Error */}
              <AnimatePresence>
                {error && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="overflow-hidden"
                  >
                    <div className="mt-2 p-3 rounded border border-[#FF3B5C]/30 bg-[#FF3B5C]/10 font-mono-tech text-[10px] text-[#FF3B5C] tracking-wide">
                      {error}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={isSubmitting || !username.trim() || !password.trim()}
                className="relative w-full h-14 mt-4 rounded overflow-hidden group disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <div className="absolute inset-0 bg-[#00E5FF]/10 transition-colors group-hover:bg-[#00E5FF]/20" />
                <div className="absolute inset-0 border border-[#00E5FF]/30 rounded transition-colors group-hover:border-[#00E5FF]/60" />
                
                {/* Border sweep effect */}
                <div className="absolute top-0 left-0 w-full h-full pointer-events-none overflow-hidden rounded">
                  <motion.div
                    animate={{ x: ['-100%', '200%'] }}
                    transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
                    className="absolute top-0 left-0 w-1/2 h-[1px] bg-gradient-to-r from-transparent via-[#00E5FF] to-transparent"
                  />
                  <motion.div
                    animate={{ x: ['200%', '-100%'] }}
                    transition={{ duration: 3, repeat: Infinity, ease: 'linear', delay: 1.5 }}
                    className="absolute bottom-0 right-0 w-1/2 h-[1px] bg-gradient-to-l from-transparent via-[#00E5FF] to-transparent"
                  />
                </div>

                <div className="relative h-full flex items-center justify-center gap-3">
                  {isSubmitting ? (
                    <>
                      <motion.div 
                        animate={{ rotate: 360 }}
                        transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
                        className="w-4 h-4 border-2 border-[#00E5FF]/30 border-t-[#00E5FF] rounded-full"
                      />
                      <span className="font-orbitron text-[11px] text-[#00E5FF] tracking-[0.2em] font-bold">
                        AUTHENTICATING
                      </span>
                    </>
                  ) : (
                    <>
                      <Key size={14} className="text-[#00E5FF]" />
                      <span className="font-orbitron text-[11px] text-[#00E5FF] tracking-[0.2em] font-bold group-hover:drop-shadow-[0_0_8px_rgba(0,229,255,0.8)] transition-all">
                        INITIALIZE SESSION
                      </span>
                    </>
                  )}
                </div>
              </button>

            </form>
          </div>
        </motion.div>
      </div>

      {/* Command Dock Hint Bottom */}
      <div className="absolute bottom-8 left-0 right-0 flex justify-center pointer-events-none opacity-40">
        <div className="font-mono-tech text-[10px] text-slate-500 tracking-[0.3em] uppercase">
          Waiting for Operator Directive
        </div>
      </div>
      
    </div>
  );
}
