/**
 * SPARK Login Page
 * ─────────────────────────────────────────────────────────────────────────────
 * Full-screen authentication gate styled with the SPARK HUD theme.
 * Orbitron headers, cyan neon inputs, scanning-line animation, boot-style
 * progress bar on submit.
 */

import { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Zap, Lock, User, Eye, EyeOff, Shield } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';

// ── Boot sequence log lines ──────────────────────────────────────────────────
const BOOT_LINES = [
  'INITIALIZING SPARK SOVEREIGN OS...',
  'LOADING COGNITIVE ENGINE...',
  'VERIFYING SECURITY CLEARANCE...',
  'ESTABLISHING ENCRYPTED CHANNEL...',
  'READY FOR AUTHENTICATION.',
];

export default function Login() {
  const navigate  = useNavigate();
  const location  = useLocation();
  const { login, isAuthenticated, error, clearError } = useAuth();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPw, setShowPw]     = useState(false);
  const [progress, setProgress] = useState(0);
  const [bootLines, setBootLines] = useState<string[]>([]);
  const [isSubmitting, setSubmitting] = useState(false);
  const progressRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Redirect if already authed
  useEffect(() => {
    if (isAuthenticated) {
      const from = (location.state as { from?: string })?.from ?? '/';
      navigate(from, { replace: true });
    }
  }, [isAuthenticated, navigate, location]);

  // Boot log animation on mount
  useEffect(() => {
    let i = 0;
    const t = setInterval(() => {
      setBootLines(prev => [...prev, BOOT_LINES[i]]);
      i++;
      if (i >= BOOT_LINES.length) clearInterval(t);
    }, 320);
    return () => clearInterval(t);
  }, []);

  const startProgress = () => {
    setProgress(0);
    progressRef.current = setInterval(() => {
      setProgress(p => {
        if (p >= 90) { clearInterval(progressRef.current!); return 90; }
        return p + Math.random() * 12;
      });
    }, 120);
  };

  const finishProgress = (success: boolean) => {
    if (progressRef.current) clearInterval(progressRef.current);
    setProgress(success ? 100 : 0);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) return;
    clearError();
    setSubmitting(true);
    startProgress();
    const ok = await login(username.trim(), password);
    finishProgress(ok);
    setSubmitting(false);
    if (ok) {
      const from = (location.state as { from?: string })?.from ?? '/';
      navigate(from, { replace: true });
    }
  };

  return (
    <div
      className="min-h-screen flex flex-col items-center justify-center relative overflow-hidden"
      style={{ background: 'radial-gradient(ellipse at center, #00022e 0%, #000814 60%, #000000 100%)' }}
    >
      {/* Grid overlay */}
      <div
        className="fixed inset-0 pointer-events-none opacity-[0.025]"
        style={{
          backgroundImage:
            'linear-gradient(hsl(186 100% 50%) 1px, transparent 1px), linear-gradient(90deg, hsl(186 100% 50%) 1px, transparent 1px)',
          backgroundSize: '60px 60px',
        }}
      />

      {/* Scanning line */}
      <div
        className="fixed inset-x-0 pointer-events-none z-0"
        style={{
          height: '2px',
          background: 'linear-gradient(90deg, transparent, hsl(186 100% 50% / 0.6), transparent)',
          animation: 'scanline 4s linear infinite',
        }}
      />

      {/* Outer glow ring */}
      <motion.div
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.6, ease: 'easeOut' }}
        className="relative z-10 w-full max-w-md px-4"
      >
        {/* ── Logo ── */}
        <div className="flex flex-col items-center mb-8">
          <motion.div
            initial={{ scale: 0.5, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: 0.1, duration: 0.5, type: 'spring' }}
            className="w-20 h-20 rounded-full border-2 border-hud-cyan flex items-center justify-center mb-4 relative"
            style={{ boxShadow: '0 0 40px hsl(186 100% 50% / 0.4), inset 0 0 20px hsl(186 100% 50% / 0.1)' }}
          >
            <Zap size={32} className="text-hud-cyan" />
            <div className="absolute inset-0 rounded-full border border-hud-cyan/30 animate-spin"
              style={{ animationDuration: '8s', borderTopColor: 'transparent', borderBottomColor: 'transparent' }} />
          </motion.div>
          <motion.div
            initial={{ y: 10, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.3, duration: 0.4 }}
          >
            <h1
              className="font-orbitron text-4xl font-black neon-text tracking-widest text-center"
              style={{ textShadow: '0 0 30px hsl(186 100% 50% / 0.8), 0 0 60px hsl(186 100% 50% / 0.3)' }}
            >
              S.P.A.R.K
            </h1>
            <p className="font-mono-tech text-[10px] text-hud-cyan/50 tracking-[0.4em] text-center mt-1 uppercase">
              Sovereign AI Operating System
            </p>
          </motion.div>
        </div>

        {/* ── Boot log ── */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4 }}
          className="mb-6 px-3 py-2 rounded border border-hud-cyan/10 bg-black/40 font-mono-tech text-[9px] h-20 overflow-hidden"
        >
          {bootLines.map((line, i) => (
            <div key={i} className="text-hud-cyan/40 leading-5">
              <span className="text-hud-cyan/60 mr-2">{'>'}</span>{line}
            </div>
          ))}
          <span className="text-hud-cyan/60 animate-pulse">█</span>
        </motion.div>

        {/* ── Login form ── */}
        <motion.form
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.6, duration: 0.4 }}
          onSubmit={handleSubmit}
          className="hud-panel rounded-lg p-6 space-y-4"
        >
          <div className="flex items-center gap-2 mb-4">
            <Shield size={14} className="text-hud-cyan/70" />
            <span className="font-orbitron text-[10px] neon-text tracking-widest uppercase">
              Authentication Required
            </span>
          </div>

          {/* Username */}
          <div className="space-y-1">
            <label className="font-orbitron text-[9px] text-hud-cyan/50 uppercase tracking-widest flex items-center gap-1">
              <User size={9} />
              Operative ID
            </label>
            <div className="relative">
              <input
                type="text"
                value={username}
                onChange={e => { setUsername(e.target.value); clearError(); }}
                autoComplete="username"
                placeholder="enter username"
                disabled={isSubmitting}
                className="w-full bg-black/60 border border-hud-cyan/30 rounded px-3 py-2 font-mono-tech text-sm text-hud-cyan placeholder-hud-cyan/20 outline-none transition-all focus:border-hud-cyan/70 focus:shadow-[0_0_10px_hsl(186_100%_50%/0.2)] disabled:opacity-50"
              />
            </div>
          </div>

          {/* Password */}
          <div className="space-y-1">
            <label className="font-orbitron text-[9px] text-hud-cyan/50 uppercase tracking-widest flex items-center gap-1">
              <Lock size={9} />
              Access Code
            </label>
            <div className="relative">
              <input
                type={showPw ? 'text' : 'password'}
                value={password}
                onChange={e => { setPassword(e.target.value); clearError(); }}
                autoComplete="current-password"
                placeholder="• • • • • • • •"
                disabled={isSubmitting}
                className="w-full bg-black/60 border border-hud-cyan/30 rounded px-3 py-2 pr-10 font-mono-tech text-sm text-hud-cyan placeholder-hud-cyan/20 outline-none transition-all focus:border-hud-cyan/70 focus:shadow-[0_0_10px_hsl(186_100%_50%/0.2)] disabled:opacity-50"
              />
              <button
                type="button"
                onClick={() => setShowPw(v => !v)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-hud-cyan/40 hover:text-hud-cyan/80 transition-colors"
              >
                {showPw ? <EyeOff size={14} /> : <Eye size={14} />}
              </button>
            </div>
          </div>

          {/* Error message */}
          <AnimatePresence>
            {error && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="rounded border border-hud-red/40 bg-hud-red/10 px-3 py-2 font-mono-tech text-[10px] text-hud-red"
              >
                ⚠ {error}
              </motion.div>
            )}
          </AnimatePresence>

          {/* Progress bar */}
          <AnimatePresence>
            {isSubmitting && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="space-y-1"
              >
                <div className="flex justify-between font-mono-tech text-[9px] text-hud-cyan/40">
                  <span>VERIFYING CREDENTIALS...</span>
                  <span>{Math.round(progress)}%</span>
                </div>
                <div className="h-1 bg-hud-cyan/10 rounded-full overflow-hidden">
                  <motion.div
                    className="h-full rounded-full bg-hud-cyan"
                    style={{ width: `${progress}%`, boxShadow: '0 0 8px hsl(186 100% 50%)' }}
                    transition={{ duration: 0.1 }}
                  />
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Submit */}
          <button
            type="submit"
            disabled={isSubmitting || !username.trim() || !password.trim()}
            className="w-full hud-btn py-2.5 rounded font-orbitron text-[11px] tracking-widest uppercase transition-all disabled:opacity-40 disabled:cursor-not-allowed"
            style={{
              background: isSubmitting
                ? 'hsl(186 100% 50% / 0.05)'
                : 'hsl(186 100% 50% / 0.08)',
              boxShadow: isSubmitting ? 'none' : '0 0 20px hsl(186 100% 50% / 0.15)',
            }}
          >
            {isSubmitting ? '◌ AUTHENTICATING...' : '⟶ INITIATE ACCESS'}
          </button>
        </motion.form>

        {/* Footer */}
        <p className="text-center font-mono-tech text-[8px] text-hud-cyan/20 mt-4 tracking-widest">
          SPARK OS v4.1 · CLASSIFIED SYSTEM · AUTHORIZED ACCESS ONLY
        </p>
      </motion.div>

      {/* Scanline keyframe */}
      <style>{`
        @keyframes scanline {
          0%   { top: -2px; opacity: 0; }
          10%  { opacity: 1; }
          90%  { opacity: 1; }
          100% { top: 100vh; opacity: 0; }
        }
      `}</style>
    </div>
  );
}
