import React, { useState } from 'react';
import {
  Globe, Terminal, Shield, Music, ChevronUp, ChevronDown, Cpu,
  Activity, Wifi, Clock, Network, Brain, Bell, Wrench, Zap, Puzzle, Globe2, Satellite
} from 'lucide-react';
import { useAlertStore } from '@/store/useAlertStore';
import { useToolActivityStore } from '@/store/useToolActivityStore';
import { useActionFeedStore } from '@/store/useActionFeedStore';

interface Props {
  onOpenModule: (m: string) => void;
  activeModule: string | null;
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

export default function BottomDock({ onOpenModule, activeModule, uptime, processes, ping }: Props) {
  const [expanded, setExpanded] = useState(false);

  const alertCount   = useAlertStore(s => s.alerts.filter(a => !a.dismissed).length);
  const pendingTools = useToolActivityStore(s => s.pendingTools.size);
  const activePlans  = useActionFeedStore(s =>
    s.plans.filter(p => p.steps.some(step => step.status === 'running')).length
  );

  // ── Primary 8 module buttons ─────────────────────────────────────────────
  const primaryButtons = [
    { id: 'spark',     icon: <Brain size={15} />,    label: 'SPARK',    color: '#00f5ff' },
    { id: 'sentinel',  icon: <Shield size={15} />,   label: 'SENTINEL', color: '#ff9f0a' },
    { id: 'globe',     icon: <Globe size={15} />,    label: 'GLOBE',    color: '#00ff88' },
    { id: 'telemetry', icon: <Activity size={15} />, label: 'TELEMETRY',color: '#00f5ff' },
    { id: 'terminal',  icon: <Terminal size={15} />, label: 'TERMINAL', color: '#aaaaaa' },
    { id: 'browser',   icon: <Globe2 size={15} />,   label: 'BROWSER',  color: '#0066ff' },
    { id: 'mind',      icon: <Network size={15} />,  label: 'MIND',     color: '#00ff88' },
    { id: 'music',     icon: <Music size={15} />,    label: 'MUSIC',    color: '#bf5af2' },
    { id: 'personal',  icon: <Brain size={15} />,    label: 'AI LINK',  color: '#ff00ff', isLink: true },
  ] as const;

  // ── Utility tray (secondary) ─────────────────────────────────────────────
  const utilityButtons = [
    { id: 'satellite',  icon: <Satellite size={13} />, label: 'SATELLITE',   badge: 0,          color: '#aaaaaa' },
    { id: 'devgraph',   icon: <Cpu size={13} />,       label: 'DEVGRAPH',    badge: 0,          color: '#bf5af2' },
    { id: 'alertlog',   icon: <Bell size={13} />,      label: 'ALERTS',      badge: alertCount,  color: alertCount   > 0 ? '#ff9f0a' : '#aaaaaa' },
    { id: 'tools',      icon: <Wrench size={13} />,    label: 'TOOLS',       badge: pendingTools,color: pendingTools > 0 ? '#00f5ff' : '#aaaaaa' },
    { id: 'actionfeed', icon: <Zap size={13} />,       label: 'ACTION FEED', badge: activePlans, color: activePlans  > 0 ? '#00f5ff' : '#aaaaaa' },
    { id: 'plugins',    icon: <Puzzle size={13} />,    label: 'PLUGINS',     badge: 0,          color: '#bf5af2' },
  ];

  return (
    <footer
      className="relative z-20 animate-boot-up"
      style={{
        background: 'rgba(0,5,20,0.90)',
        backdropFilter: 'blur(16px)',
        borderTop: '1px solid hsl(186 100% 50% / 0.25)',
        boxShadow: '0 -2px 30px hsl(186 100% 50% / 0.08)',
        animationDelay: '0.2s',
      }}
    >
      {/* Utility tray (collapsible) */}
      <div
        className={`overflow-hidden transition-all duration-300 ${expanded ? 'max-h-12' : 'max-h-0'}`}
        style={{ borderBottom: expanded ? '1px solid rgba(0,245,255,0.12)' : 'none' }}
      >
        <div className="flex items-center justify-center gap-2 py-1.5 px-4">
          {utilityButtons.map(btn => (
            <button
              key={btn.id}
              onClick={() => onOpenModule(btn.id)}
              className="relative flex items-center gap-1.5 px-3 py-1 rounded transition-all font-orbitron text-[8px] tracking-wider border"
              style={{
                borderColor: activeModule === btn.id ? `${btn.color}60` : 'rgba(0,245,255,0.12)',
                color: activeModule === btn.id ? btn.color : 'rgba(0,245,255,0.45)',
                background: activeModule === btn.id ? `${btn.color}12` : 'transparent',
              }}
            >
              {btn.icon}
              {btn.label}
              {btn.badge > 0 && (
                <span
                  className="absolute -top-1 -right-1 min-w-[14px] h-3.5 rounded-full font-orbitron text-[7px] flex items-center justify-center px-0.5"
                  style={{ background: btn.color, color: '#000' }}
                >
                  {btn.badge}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Main dock bar */}
      <div className="flex items-center justify-between px-3 py-1.5">
        {/* Status indicators */}
        <div className="flex items-center gap-3 shrink-0">
          <div className="flex items-center gap-1">
            <Clock size={9} className="text-hud-cyan/50" />
            <span className="font-mono-tech text-[9px] text-hud-cyan/60">{formatUptime(uptime)}</span>
          </div>
          <div className="flex items-center gap-1">
            <Cpu size={9} className="text-hud-cyan/50" />
            <span className="font-mono-tech text-[9px] text-hud-cyan/60">{processes}P</span>
          </div>
          <div className="flex items-center gap-1">
            <Wifi size={9} className={ping > 100 ? 'text-hud-red' : ping > 50 ? 'text-hud-amber' : 'text-hud-green'} />
            <span className="font-mono-tech text-[9px] text-hud-cyan/60">{ping}ms</span>
          </div>
          <div className="w-1.5 h-1.5 rounded-full bg-hud-green animate-pulse" />
        </div>

        {/* Primary module buttons */}
        <div className="flex items-center gap-0.5">
          {primaryButtons.map((btn, i) => {
            const isActive = activeModule === btn.id;
            const showSep = i === 3 || i === 5 || i === 6;
            return (
              <React.Fragment key={btn.id}>
                {showSep && (
                  <div className="w-px h-5 mx-1" style={{ background: 'rgba(0,245,255,0.1)' }} />
                )}
                <button
                  onClick={() => 'isLink' in btn && btn.isLink ? window.location.href = '/personal' : onOpenModule(btn.id)}
                  className="relative flex flex-col items-center gap-0.5 px-2.5 py-1.5 rounded transition-all"
                  style={{ color: isActive ? btn.color : 'rgba(0,245,255,0.4)' }}
                >
                  <div className="transition-transform" style={{ transform: isActive ? 'scale(1.1)' : 'scale(1)' }}>
                    {btn.icon}
                  </div>
                  <span className="font-orbitron text-[7px] tracking-wider leading-none">{btn.label}</span>
                  {isActive && (
                    <span
                      className="absolute bottom-0 left-2 right-2 h-0.5 rounded-t-full"
                      style={{ background: btn.color, boxShadow: `0 0 6px ${btn.color}` }}
                    />
                  )}
                </button>
              </React.Fragment>
            );
          })}
        </div>

        {/* Expand toggle + alert indicator */}
        <div className="flex items-center gap-2 shrink-0">
          {alertCount > 0 && (
            <button
              onClick={() => onOpenModule('alertlog')}
              className="flex items-center gap-1 font-orbitron text-[8px] px-2 py-1 rounded border border-hud-amber/40 text-hud-amber animate-pulse"
            >
              <Bell size={10} /> {alertCount}
            </button>
          )}
          <button
            onClick={() => setExpanded(v => !v)}
            className="flex items-center gap-1 font-orbitron text-[8px] text-hud-cyan/50 hover:text-hud-cyan transition-colors px-2 py-1 rounded border border-hud-cyan/15 hover:border-hud-cyan/40"
          >
            {expanded ? <ChevronDown size={9} /> : <ChevronUp size={9} />}
          </button>
        </div>
      </div>
    </footer>
  );
}
