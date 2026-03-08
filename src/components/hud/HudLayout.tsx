import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import ParticleBackground from './ParticleBackground';
import TopBar from './TopBar';
import BottomDock from './BottomDock';
import CoreModule from './CoreModule';
import SystemPanel from './SystemPanel';
import ControlPanel from './ControlPanel';
import AIPanelSlider from './AIPanelSlider';
import SatelliteModule from './modules/SatelliteModule';
import DevGraphModule from './modules/DevGraphModule';
import AlertLogPanel from './modules/AlertLogPanel';
import ToolActivityPanel from './modules/ToolActivityPanel';
import ActionFeedPanel from './modules/ActionFeedPanel';
import PluginsModule from './modules/PluginsModule';
import BrowserModule from './modules/BrowserModule';
import MusicModule from './modules/MusicModule';
import SparkPanel from './modules/SparkPanel';
import SentinelModule from './modules/SentinelModule';
import TelemetryModule from './modules/TelemetryModule';
import MindModule from './modules/MindModule';
import SparkAlertToast from './SparkAlertToast';
import AgentConfirmModal from './AgentConfirmModal';
import CommandBar from './CommandBar';
import { useSystemMetrics } from '@/hooks/useSystemMetrics';
import { useVoiceEngine } from '@/hooks/useVoiceEngine';
import { useHudTheme } from '@/contexts/ThemeContext';
import { useAIEvents } from '@/hooks/useAIEvents';
import { useAgentConfirmStore } from '@/store/useAgentConfirmStore';
import { useCommanderContext } from '@/hooks/useCommanderContext';
import { useFxStore } from '@/store/useFxStore';
import { useCommandBarStore } from '@/store/commandBarStore';
import { useWakeWordListener } from '@/hooks/useWakeWordListener';
import { Brain } from 'lucide-react';

type ModuleKey = 'spark' | 'sentinel' | 'telemetry' | 'mind' | 'satellite' | 'devgraph' | 'alertlog' | 'tools' | 'actionfeed' | 'plugins' | 'browser' | 'music';

const MODULE_TITLES: Record<ModuleKey, string> = {
  spark:      '⚡ SPARK AGENT',
  sentinel:   '🔐 SENTINEL',
  telemetry:  '📡 TELEMETRY',
  mind:       '🧠 MIND',
  satellite:  '🛰 SATELLITE TRACKER',
  devgraph:   '🕸️ DEV OS GRAPH',
  alertlog:   '🔔 SYSTEM ALERTS',
  tools:      '⚙ TOOL EXECUTION',
  actionfeed: '⚡ ACTION FEED',
  plugins:    '🧩 PLUGIN MANAGER',
  browser:    '🌐 BROWSER AGENT',
  music:      '🎵 MUSIC PLAYER',
};

export default function HudLayout() {
  const metrics = useSystemMetrics();
  const voice = useVoiceEngine();
  const { aiMode, isBooted, isShuttingDown } = useHudTheme();
  const [activeModule, setActiveModule] = useState<ModuleKey | null>(null);
  const [isMaximized, setIsMaximized] = useState(false);
  const [showAiPanel, setShowAiPanel] = useState(false);
  const navigate = useNavigate();
  const { setOpen: setCommandBarOpen } = useCommandBarStore();

  const commanderCtx = useCommanderContext(
    { cpu: metrics.cpu, ram: metrics.ram, ping: metrics.ping },
    activeModule,
  );

  // ── Global event listeners ───────────────────────────────────────────────
  useAIEvents();                                   // listens to /ws/ai → tool store
  useWakeWordListener();                           // listens for WAKE_WORD_DETECTED → opens CommandBar
  const { pendingRequest, setPending } = useAgentConfirmStore();
  // ── SPARK FX queue consumer ───────────────────────────────────────
  const fxQueue      = useFxStore((s) => s.queue);
  const consumeFx    = useFxStore((s) => s.consumeFx);
  const setFocusMode = useFxStore((s) => s.setFocusMode);
  const focusMode    = useFxStore((s) => s.focusMode);

  useEffect(() => {
    if (!fxQueue.length) return;
    const item = fxQueue[0];
    switch (item.fx) {
      case 'NAVIGATE_GLOBE':      navigate('/globe-monitor'); break;
      case 'NAVIGATE_ALERTS':     setActiveModule('alertlog'); setIsMaximized(false); break;
      case 'NAVIGATE_TOOLS':      setActiveModule('tools');    setIsMaximized(false); break;
      case 'NAVIGATE_ACTIONFEED': setActiveModule('actionfeed'); setIsMaximized(false); break;
      case 'FOCUS_MODE_ON':       setFocusMode(true);  break;
      case 'FOCUS_MODE_OFF':      setFocusMode(false); break;
    }
    consumeFx(item.id);
  }, [fxQueue, consumeFx, setFocusMode, navigate]);
  // ── Ctrl+Space → CommandBar ──────────────────────────────────────────────
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.code === 'Space' && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        setCommandBarOpen(v => !v);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [setCommandBarOpen]);

  // ── Module activation via custom events from CommandBar ─────────────────
  useEffect(() => {
    const handler = (evt: Event) => {
      const event = evt as CustomEvent;
      const { module, action, params } = event.detail;
      
      // Handle module-specific activation
      if (module === 'globe') {
        navigate('/globe-monitor');
      } else if (module === 'music' && params?.query) {
        setActiveModule('music');
        window.dispatchEvent(new CustomEvent('music-play', { detail: { query: params.query } }));
      } else if (module === 'browser' && params?.url) {
        setActiveModule('browser');
        window.dispatchEvent(new CustomEvent('browser-navigate', { detail: { url: params.url } }));
      } else if (module === 'neural_search' && params?.query) {
        setActiveModule('mind');
        window.dispatchEvent(new CustomEvent('search-query', { detail: { query: params.query } }));
      } else if (module === 'scheduler') {
        setActiveModule('mind');
        window.dispatchEvent(new CustomEvent('scheduler-action', { detail: params }));
      } else if (module === 'security') {
        setActiveModule('sentinel');
        window.dispatchEvent(new CustomEvent('security-action', { detail: { action } }));
      } else if (module === 'agent' || module === 'llm') {
        setActiveModule('spark');
        if (module === 'llm') setShowAiPanel(true);
        window.dispatchEvent(new CustomEvent('llm-query', { detail: { query: params?.query } }));
      } else if (module === 'mode') {
        window.dispatchEvent(new CustomEvent('mode-activate', { detail: params }));
      } else if (module === 'plugin') {
        window.dispatchEvent(new CustomEvent('plugin-action', { detail: params }));
      }
      setIsMaximized(false);
    };
    
    window.addEventListener('module-activate', handler);
    return () => window.removeEventListener('module-activate', handler);
  }, [navigate]);

  const openModule = (m: string) => {
    if (m === 'globe') {
      navigate('/globe-monitor');
      return;
    }
    if (m === 'os') {
      navigate('/cognitive');
      return;
    }
    setActiveModule(m as ModuleKey);
    setIsMaximized(false);
  };

  const closeModule = () => {
    setActiveModule(null);
    setIsMaximized(false);   // always reset when closing
  };

  const toggleMaximize = () => setIsMaximized(v => !v);

  return (
    <div className="relative w-full h-screen flex flex-col overflow-hidden"
      style={{ background: 'radial-gradient(ellipse at center, #00022e 0%, #000814 60%, #000000 100%)' }}>

      {isShuttingDown && (
        <div className="fixed inset-0 z-[200] bg-black/80 flex items-center justify-center animate-pulse">
          <div className="font-orbitron text-hud-red text-2xl tracking-widest">SYSTEM SHUTDOWN</div>
        </div>
      )}

      {/* Focus Mode banner */}
      {focusMode && (
        <div
          className="fixed top-10 left-1/2 -translate-x-1/2 z-[90] flex items-center gap-2 px-3 py-1 rounded border"
          style={{ background: '#1a0f00', borderColor: '#ff9f0a40', boxShadow: '0 0 20px #ff9f0a18' }}
        >
          <span className="font-orbitron text-[8px] text-hud-amber tracking-widest">FOCUS MODE</span>
          <span className="font-mono-tech text-[8px] text-hud-amber/50">· CRIT ONLY</span>
          <button
            onClick={() => setFocusMode(false)}
            className="font-orbitron text-[7px] text-hud-amber/40 hover:text-hud-amber/80 ml-1 transition-colors"
          >
            ✕
          </button>
        </div>
      )}

      <ParticleBackground count={120} />

      {/* Grid overlay */}
      <div className="fixed inset-0 pointer-events-none z-[1] opacity-[0.025]"
        style={{ backgroundImage: 'linear-gradient(hsl(186 100% 50%) 1px, transparent 1px), linear-gradient(90deg, hsl(186 100% 50%) 1px, transparent 1px)', backgroundSize: '60px 60px' }} />

      {/* Top bar */}
      <div className="z-20 shrink-0">
        <TopBar
          ttsEnabled={voice.ttsEnabled}
          onToggleTts={() => voice.setTtsEnabled(!voice.ttsEnabled)}
          onMicTranscript={(transcript) => voice.processInput(transcript)}
        />
      </div>

      {/* Main content */}
      <div className="flex-1 flex gap-1.5 px-1.5 py-1 min-h-0 z-10 relative">
        {/* LEFT PANEL */}
        <div className="w-56 shrink-0 hud-panel rounded overflow-hidden">
          <SystemPanel metrics={metrics} />
        </div>

        {/* CENTER */}
        <div className="flex-1 flex flex-col gap-1.5 min-w-0">
          {/* Core module */}
          <div className="flex-1 hud-panel rounded flex items-center justify-center relative overflow-hidden">
            <CoreModule
              status={voice.status}
              isListening={voice.isListening}
              amplitude={voice.amplitude}
              onToggleMic={voice.toggleMic}
              aiMode={aiMode}
            />
            {/* AI Panel button */}
            <button
              onClick={() => setShowAiPanel(v => !v)}
              className="absolute top-2 right-2 hud-btn p-1.5 rounded"
              title="AI Personality Panel"
            >
              <Brain size={14} />
            </button>
          </div>

          {/* Module overlay */}
          <AnimatePresence>
            {activeModule && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 20 }}
                className={isMaximized
                  ? "fixed inset-0 z-50 hud-panel-glow rounded overflow-hidden bg-black/95 backdrop-blur-xl"
                  : "absolute inset-x-[232px] bottom-14 top-14 z-30 hud-panel-glow rounded overflow-hidden"}
              >
                <div className="flex items-center justify-between px-3 py-2 border-b border-hud-cyan/20 bg-hud-black/50">
                  <span className="font-orbitron text-[10px] neon-text">{MODULE_TITLES[activeModule]}</span>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={toggleMaximize}
                      className="font-orbitron text-[10px] text-hud-cyan/60 hover:text-hud-cyan transition-colors px-2 py-0.5 border border-hud-cyan/20 hover:border-hud-cyan/60 rounded"
                    >
                      {isMaximized ? '▼ MINIMISE' : '▲ MAXIMISE'}
                    </button>
                    <button
                      onClick={closeModule}
                      className="font-orbitron text-[10px] text-hud-cyan/60 hover:text-hud-red transition-colors px-2 py-0.5 border border-hud-cyan/20 hover:border-hud-red/60 rounded"
                    >
                      ✕ CLOSE
                    </button>
                  </div>
                </div>
                <div className="h-[calc(100%-36px)] overflow-hidden relative">
                  {activeModule === 'spark'      && <SparkPanel />}
                  {activeModule === 'sentinel'   && <SentinelModule />}
                  {activeModule === 'telemetry'  && <TelemetryModule />}
                  {activeModule === 'mind'        && <MindModule />}
                  {activeModule === 'satellite'  && <SatelliteModule />}
                  {activeModule === 'devgraph'   && <DevGraphModule />}
                  {activeModule === 'alertlog'   && <AlertLogPanel />}
                  {activeModule === 'tools'      && <ToolActivityPanel />}
                  {activeModule === 'actionfeed' && <ActionFeedPanel />}
                  {activeModule === 'plugins'    && <PluginsModule />}
                  {activeModule === 'browser'    && <BrowserModule />}
                  {activeModule === 'music'      && <MusicModule />}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* RIGHT PANEL */}
        <div className="w-56 shrink-0 hud-panel rounded overflow-hidden">
          <ControlPanel
            commandHistory={voice.commandHistory}
            aiResponse={voice.aiResponse}
            transcript={voice.transcript}
            onProcessInput={voice.processInput}
            status={voice.status}
          />
        </div>
      </div>

      {/* Bottom dock */}
      <div className="z-20 shrink-0">
        <BottomDock onOpenModule={openModule} activeModule={activeModule} uptime={metrics.uptime} processes={metrics.processes} ping={metrics.ping} />
      </div>

      {/* AI personality panel */}
      <AnimatePresence>
        {showAiPanel && (
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="fixed right-0 top-0 bottom-0 z-[60]"
          >
            <AIPanelSlider onClose={() => setShowAiPanel(false)} />
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Global overlays ─────────────────────────────────────────────────── */}
      {/* Alert toasts — always mounted, shows on incoming ALERT frames */}
      <SparkAlertToast />

      {/* Desktop Agent confirm modal */}
      <AgentConfirmModal
        request={pendingRequest}
        onClose={() => setPending(null)}
      />

      {/* Global command bar — Ctrl+Space (renders via Zustand store) */}
      <CommandBar />
    </div>
  );
}
