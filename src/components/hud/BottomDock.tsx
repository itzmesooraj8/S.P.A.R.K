import { useState, useEffect, useRef } from 'react';
import {
  Globe, Chrome, Terminal, Power, Lock, Rocket,
  Shield, Music, ChevronUp, ChevronDown, Cpu,
  Activity, Wifi, Thermometer, Clock, Network, Brain,
  Bell, Wrench, Zap, Puzzle, Globe2
} from 'lucide-react';
import { useAlertStore } from '@/store/useAlertStore';
import { useToolActivityStore } from '@/store/useToolActivityStore';
import { useActionFeedStore } from '@/store/useActionFeedStore';

interface QuickButton {
  icon: React.ReactNode;
  label: string;
  action: () => void;
  color?: string;
}

interface Props {
  onOpenModule: (m: string) => void;
  uptime: number;
  processes: number;
  ping: number;
}

function formatUptime(ms: number) {
  const s = Math.floor(ms / 1000);
  const h = Math.floor(s / 3600).toString().padStart(2, '0');
  const m = Math.floor((s % 3600) / 60).toString().padStart(2, '0');
  const sec = (s % 60).toString().padStart(2, '0');
  return `${h}:${m}:${sec}`;
}

export default function BottomDock({ onOpenModule, uptime, processes, ping }: Props) {
  const [expanded, setExpanded] = useState(false);
  const [activeBtn, setActiveBtn] = useState<string | null>(null);

  const alertCount   = useAlertStore(s => s.alerts.filter(a => !a.dismissed).length);
  const pendingTools = useToolActivityStore(s => s.pendingTools.size);
  const activePlans  = useActionFeedStore(s =>
    s.plans.filter(p => p.steps.some(step => step.status === 'running')).length
  );

  const quickButtons: QuickButton[] = [
    { icon: <Globe size={16} />, label: 'BROWSER', action: () => window.open('about:blank') },
    { icon: <Terminal size={16} />, label: 'TERMINAL', action: () => { } },
    { icon: <Shield size={16} />, label: 'SECURITY', action: () => onOpenModule('security'), color: 'hud-green' },
    { icon: <Lock size={16} />, label: 'LOCK', action: () => { }, color: 'hud-amber' },
    { icon: <Rocket size={16} />, label: 'LAUNCH', action: () => { } },
    { icon: <Activity size={16} />, label: 'SCAN', action: () => onOpenModule('analytics') },
    { icon: <Music size={16} />, label: 'MUSIC', action: () => { } },
    { icon: <Globe size={16} />, label: 'GLOBE', action: () => onOpenModule('globe') },
  ];

  const secondaryButtons: QuickButton[] = [
    { icon: <Cpu size={14} />, label: 'AGENT', action: () => onOpenModule('agent') },
    { icon: <Wifi size={14} />, label: 'DATASTREAM', action: () => onOpenModule('datastream') },
    { icon: <Activity size={14} />, label: 'SATELLITE', action: () => onOpenModule('satellite') },
    { icon: <Terminal size={14} />, label: 'AI LOG', action: () => onOpenModule('reasoning') },
    { icon: <Network size={14} />, label: 'DEVGRAPH', action: () => onOpenModule('devgraph'), color: 'hud-purple' },
    { icon: <Shield size={14} />, label: 'TACTICAL', action: () => onOpenModule('tactical'), color: 'hud-red' },
    { icon: <Brain size={14} />, label: 'OS CORE', action: () => onOpenModule('os'), color: 'hud-cyan' },
    { icon: <Bell size={14} />,  label: 'ALERTS',      action: () => onOpenModule('alertlog'),    color: alertCount > 0  ? 'hud-amber' : undefined },
    { icon: <Wrench size={14} />,label: 'TOOLS',       action: () => onOpenModule('tools'),       color: pendingTools > 0 ? 'hud-cyan'  : undefined },
    { icon: <Zap size={14} />,   label: 'ACTION FEED', action: () => onOpenModule('actionfeed'),  color: activePlans > 0  ? 'hud-cyan'  : undefined },
    { icon: <Puzzle size={14} />,label: 'PLUGINS',     action: () => onOpenModule('plugins'),     color: 'hud-purple' },
    { icon: <Clock size={14} />, label: 'SCHEDULER',   action: () => onOpenModule('scheduler'),   color: 'hud-amber'  },
    { icon: <Globe2 size={14} />,label: 'BROWSER',     action: () => onOpenModule('browser'),     color: 'hud-cyan'   },
    { icon: <Brain size={14} />, label: 'NEURAL SEARCH',action: () => onOpenModule('neuralsearch'),color: 'hud-green'  },
  ];

  const handleBtn = (btn: QuickButton) => {
    setActiveBtn(btn.label);
    btn.action();
    setTimeout(() => setActiveBtn(null), 500);
  };

  return (
    <footer
      className="relative z-20 animate-boot-up"
      style={{
        background: 'rgba(0,5,20,0.85)',
        backdropFilter: 'blur(16px)',
        borderTop: '1px solid hsl(186 100% 50% / 0.3)',
        boxShadow: '0 -2px 30px hsl(186 100% 50% / 0.1)',
        animationDelay: '0.2s',
      }}
    >
      {/* Secondary tray */}
      <div
        className={`overflow-hidden transition-all duration-300 ${expanded ? 'max-h-16' : 'max-h-0'}`}
        style={{ borderBottom: expanded ? '1px solid hsl(186 100% 50% / 0.2)' : 'none' }}
      >
        <div className="flex items-center justify-center gap-3 py-2 px-4">
          {secondaryButtons.map(btn => {
            const badge =
              btn.label === 'ALERTS'       && alertCount > 0   ? alertCount  :
              btn.label === 'TOOLS'        && pendingTools > 0  ? pendingTools :
              btn.label === 'ACTION FEED'  && activePlans > 0   ? activePlans  :
              null;
            return (
              <button
                key={btn.label}
                onClick={() => handleBtn(btn)}
                className="hud-btn flex-row gap-1.5 px-3 py-1.5 relative"
              >
                {btn.icon}
                <span className="font-orbitron text-[8px] tracking-wider">{btn.label}</span>
                {badge !== null && (
                  <span
                    className="absolute -top-0.5 -right-0.5 min-w-[14px] h-3.5 rounded-full font-orbitron text-[7px] flex items-center justify-center px-0.5"
                    style={{
                      background: btn.label === 'ALERTS' ? '#ff9f0a' : '#00f5ff',
                      color: '#000',
                    }}
                  >
                    {badge}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      <div className="flex items-center justify-between px-4 py-2">
        {/* Status indicators */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5">
            <Clock size={10} className="text-hud-cyan/60" />
            <span className="font-mono-tech text-[10px] text-hud-cyan/70">{formatUptime(uptime)}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Cpu size={10} className="text-hud-cyan/60" />
            <span className="font-mono-tech text-[10px] text-hud-cyan/70">{processes} PROC</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Wifi size={10} className={ping > 100 ? 'text-hud-red' : ping > 50 ? 'text-hud-amber' : 'text-hud-green'} />
            <span className="font-mono-tech text-[10px] text-hud-cyan/70">{ping}ms</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-1 h-1 rounded-full bg-hud-green animate-pulse" />
            <span className="font-mono-tech text-[9px] text-hud-green/80">SYS NOMINAL</span>
          </div>
        </div>

        {/* Quick buttons */}
        <div className="flex items-center gap-1.5">
          {quickButtons.map(btn => (
            <button
              key={btn.label}
              onClick={() => handleBtn(btn)}
              className={`hud-btn transition-all duration-150 ${activeBtn === btn.label ? 'scale-95 opacity-60' : ''}`}
              style={{ minWidth: '52px' }}
            >
              {btn.icon}
              <span className="font-orbitron text-[7px] tracking-wider leading-none">{btn.label}</span>
            </button>
          ))}
        </div>

        {/* Expand toggle */}
        <button
          onClick={() => setExpanded(v => !v)}
          className="flex items-center gap-1 font-orbitron text-[9px] text-hud-cyan/60 hover:text-hud-cyan transition-colors px-2 py-1 rounded border border-hud-cyan/20 hover:border-hud-cyan/50"
        >
          {expanded ? <ChevronDown size={10} /> : <ChevronUp size={10} />}
          <span>{expanded ? 'COLLAPSE' : 'EXPAND'}</span>
        </button>
      </div>
    </footer>
  );
}
