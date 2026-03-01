import { useState, useEffect } from 'react';
import { useHudTheme } from '@/contexts/ThemeContext';
import { MapPin, Sun, Wind, Zap, FolderKey, LogOut, User } from 'lucide-react';
import { useDevState } from '@/hooks/useDevState';
import { useAuth } from '@/contexts/AuthContext';

const MONTHS = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'];

function FlipDigits({ value }: { value: string }) {
  return (
    <span className="inline-flex gap-0.5">
      {value.split('').map((d, i) => (
        <span
          key={i}
          className="font-orbitron text-hud-cyan inline-block w-[0.85em] text-center"
          style={{ textShadow: '0 0 8px hsl(186 100% 50% / 0.8), 0 0 20px hsl(186 100% 50% / 0.4)' }}
        >
          {d}
        </span>
      ))}
    </span>
  );
}

export default function TopBar() {
  const { theme, setTheme, aiMode, setAiMode } = useHudTheme();
  const { user, isAuthenticated, logout } = useAuth();
  const [now, setNow] = useState(new Date());

  const [projects, setProjects] = useState<string[]>([]);
  const [focusedProject, setFocusedProject] = useState<string | null>(null);

  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000);

    // Fetch initial projects
    const fetchProjects = async () => {
      // Skip polling while the tab is in the background
      if (document.visibilityState === 'hidden') return;
      try {
        const res = await fetch('http://localhost:8000/api/projects');
        if (res.ok) {
          const data = await res.json();
          setProjects(data.active_projects || []);
          setFocusedProject(data.current_focus);
        }
      } catch (err) {
        console.warn('Failed to fetch projects', err);
      }
    };
    fetchProjects();
    // Poll every 8s; skip silently when tab is hidden (visibilityState guard above)
    const p = setInterval(fetchProjects, 8000);

    // Re-fetch immediately when the tab becomes visible again
    const onVisible = () => { if (document.visibilityState === 'visible') fetchProjects(); };
    document.addEventListener('visibilitychange', onVisible);

    return () => { clearInterval(t); clearInterval(p); document.removeEventListener('visibilitychange', onVisible); };
  }, []);

  const switchProject = async (id: string) => {
    try {
      setFocusedProject(id); // Optimistic UI
      await fetch(`http://localhost:8000/api/projects/switch/${id}`, { method: 'POST' });
    } catch (err) {
      console.error('Failed to switch focus', err);
    }
  };

  const hh = now.getHours();
  const ampm = hh >= 12 ? 'PM' : 'AM';
  const hh12 = hh % 12 || 12;
  const hhStr = hh12.toString().padStart(2, '0');
  const mm = now.getMinutes().toString().padStart(2, '0');
  const ss = now.getSeconds().toString().padStart(2, '0');
  const dateStr = `${now.getDate().toString().padStart(2, '0')}.${MONTHS[now.getMonth()]}.${now.getFullYear()}`;

  const modeColors: Record<string, string> = {
    PASSIVE: 'text-hud-cyan border-hud-cyan',
    ACTIVE: 'text-hud-amber border-hud-amber',
    COMBAT: 'text-hud-red border-hud-red',
  };

  return (
    <header
      className="relative z-20 flex items-center justify-between px-4 py-1.5 animate-boot-down"
      style={{
        background: 'rgba(0,5,20,0.85)',
        backdropFilter: 'blur(16px)',
        borderBottom: '1px solid hsl(186 100% 50% / 0.3)',
        boxShadow: '0 2px 30px hsl(186 100% 50% / 0.1)',
        animationDelay: '0.1s',
      }}
    >
      {/* Grid overlay */}
      <div className="absolute inset-0 pointer-events-none opacity-5"
        style={{ backgroundImage: 'linear-gradient(hsl(186 100% 50%) 1px, transparent 1px), linear-gradient(90deg, hsl(186 100% 50%) 1px, transparent 1px)', backgroundSize: '40px 40px' }} />

      {/* LEFT: Logo + Status */}
      <div className="flex items-center gap-4 min-w-0">
        <div className="flex items-center gap-2">
          <div className="relative">
            <div className="w-8 h-8 rounded-full border-2 border-hud-cyan flex items-center justify-center animate-pulse-glow">
              <Zap size={14} className="text-hud-cyan" />
            </div>
            <div className="absolute inset-0 rounded-full animate-pulse-ring border border-hud-cyan opacity-50" />
          </div>
          <div>
            <div className="font-orbitron text-sm font-bold neon-text tracking-widest">SPARK</div>
            <div className="font-mono-tech text-[9px] text-hud-cyan/60 tracking-wider">v4.1 · ONLINE</div>
          </div>
        </div>

        {/* AI Mode */}
        <div className="flex gap-1">
          {(['PASSIVE', 'ACTIVE', 'COMBAT'] as const).map(mode => (
            <button
              key={mode}
              onClick={() => setAiMode(mode)}
              className={`font-orbitron text-[9px] px-2 py-0.5 rounded border tracking-wider transition-all duration-200 ${aiMode === mode
                ? `${modeColors[mode]} bg-current/10`
                : 'text-hud-cyan/40 border-hud-cyan/20 hover:border-hud-cyan/50'
                }`}
            >
              {mode}
            </button>
          ))}
        </div>

        {/* Project Switcher */}
        <div className="flex items-center gap-1.5 ml-4 px-2 py-0.5 rounded border border-hud-purple/40 bg-hud-purple/5">
          <FolderKey size={10} className="text-hud-purple" />
          <span className="font-orbitron text-[8px] text-hud-purple/70">DOMAIN:</span>
          <select
            value={focusedProject || ''}
            onChange={(e) => switchProject(e.target.value)}
            className="bg-transparent font-mono-tech text-[9px] text-hud-purple outline-none cursor-pointer"
            style={{ WebkitAppearance: 'none' }}
          >
            <option value="" disabled className="bg-black text-hud-purple">SELECT DOMAIN...</option>
            {projects.map(p => (
              <option key={p} value={p} className="bg-black text-hud-purple">{p.toUpperCase()}</option>
            ))}
          </select>
        </div>
      </div>

      {/* CENTER: Clock */}
      <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 flex flex-col items-center">
        <div className="flex items-center gap-1 font-orbitron text-xl font-bold">
          <FlipDigits value={hhStr} />
          <span className="neon-text animate-blink">:</span>
          <FlipDigits value={mm} />
          <span className="neon-text animate-blink">:</span>
          <FlipDigits value={ss} />
          <span className="ml-2 text-xs text-hud-cyan/70">{ampm}</span>
        </div>
        <div className="font-rajdhani text-[10px] text-hud-cyan/60 tracking-widest mt-0.5">{dateStr}</div>
      </div>

      {/* RIGHT: Location + Weather + Theme */}
      <div className="flex items-center gap-4 min-w-0">
        {/* Location */}
        <div className="flex items-center gap-1">
          <MapPin size={10} className="text-hud-cyan animate-blink" />
          <div className="font-mono-tech text-[9px] text-hud-cyan/70">
            <span>40.7128° N</span>
            <span className="mx-1 text-hud-cyan/30">|</span>
            <span>74.0060° W</span>
          </div>
        </div>

        {/* Weather */}
        <div className="flex items-center gap-1.5 px-2 py-0.5 rounded border border-hud-cyan/20">
          <Sun size={12} className="text-hud-amber" />
          <span className="font-rajdhani text-xs text-hud-cyan/80">22°C</span>
          <span className="font-rajdhani text-[9px] text-hud-cyan/40">CLEAR</span>
          <div className="flex items-center gap-0.5">
            <Wind size={9} className="text-hud-cyan/40" />
            <span className="font-mono-tech text-[8px] text-hud-cyan/40">12km/h</span>
          </div>
        </div>

        {/* Theme selector */}
        <div className="flex gap-1">
          {([['blue', '#00f5ff', 'B'], ['red', '#ff3b3b', 'R'], ['white', '#e0e0e0', 'W']] as const).map(([t, color, label]) => (
            <button
              key={t}
              onClick={() => setTheme(t)}
              className={`w-5 h-5 rounded-sm border text-[9px] font-orbitron font-bold transition-all duration-200 ${theme === t ? 'opacity-100 scale-110' : 'opacity-40 hover:opacity-70'
                }`}
              style={{ borderColor: color, color, backgroundColor: `${color}22` }}
            >
              {label}
            </button>
          ))}
        </div>

        {/* User badge + logout */}
        {isAuthenticated && user && (
          <div className="flex items-center gap-1.5 pl-3 border-l border-hud-cyan/20">
            <div className="flex items-center gap-1 px-2 py-0.5 rounded border border-hud-cyan/20 bg-hud-cyan/5">
              <User size={9} className="text-hud-cyan/60" />
              <span className="font-orbitron text-[9px] text-hud-cyan/70 tracking-widest uppercase">
                {user.username}
              </span>
              <span
                className="font-orbitron text-[7px] px-1 rounded border ml-1"
                style={{
                  borderColor: user.role === 'admin' ? '#ff9f0a50' : '#00f5ff30',
                  color:       user.role === 'admin' ? '#ff9f0a'   : '#00f5ff80',
                  background:  user.role === 'admin' ? '#ff9f0a10' : '#00f5ff08',
                }}
              >
                {user.role.toUpperCase()}
              </span>
            </div>
            <button
              onClick={logout}
              title="Logout"
              className="text-hud-cyan/30 hover:text-hud-red/80 transition-colors p-1 rounded"
            >
              <LogOut size={10} />
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
