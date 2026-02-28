/**
 * SnapshotPlayback — Historical snapshot browser + timeline slider.
 * Snapshots are saved to IndexedDB; metadata is in Zustand store.
 *
 * UI:
 *   - SAVE button: create snapshot of current live data
 *   - Timeline slider: scrub through saved snapshots
 *   - LIVE button: exit playback mode
 *   - Each snapshot shows label, mode, event count, time
 */
import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Camera, Play, Square, ChevronLeft, ChevronRight, Trash2, History } from 'lucide-react';
import { useMonitorStore } from '@/store/useMonitorStore';
import { useSnapshotStore, type SnapshotData } from '@/hooks/useSnapshotStore';

interface SnapshotPlaybackProps {
  accentColor?: string;
}

export const SnapshotPlayback = ({ accentColor = '#00f5ff' }: SnapshotPlaybackProps) => {
  const { snapshots, playbackIndex, setPlaybackIndex, saveSnapshot, loadSnapshot, deleteSnapshot } =
    useSnapshotStore();

  const [saving,       setSaving]       = useState(false);
  const [loadedData,   setLoadedData]   = useState<SnapshotData | null>(null);
  const [isExpanded,   setIsExpanded]   = useState(false);

  const isPlayback = playbackIndex !== null;

  const handleSave = async () => {
    setSaving(true);
    await saveSnapshot();
    setSaving(false);
  };

  const handleSelectSnapshot = async (index: number) => {
    setPlaybackIndex(index);
    const meta = snapshots[index];
    if (meta) {
      const data = await loadSnapshot(meta.id);
      setLoadedData(data ?? null);
    }
  };

  const handleLive = () => {
    setPlaybackIndex(null);
    setLoadedData(null);
  };

  const handleStep = (dir: -1 | 1) => {
    if (playbackIndex === null) return;
    const next = Math.max(0, Math.min(snapshots.length - 1, playbackIndex + dir));
    handleSelectSnapshot(next);
  };

  const handleDelete = async (index: number, id: string) => {
    await deleteSnapshot(id);
    if (playbackIndex === index) handleLive();
  };

  return (
    <div
      className="fixed bottom-6 right-3 z-40 pointer-events-auto"
      style={{ width: '16rem' }}
    >
      {/* ── Collapsed mode: compact pill ─────────────────────────────────── */}
      <AnimatePresence mode="wait">
        {!isExpanded ? (
          <motion.button
            key="pill"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
            onClick={() => setIsExpanded(true)}
            className="flex items-center gap-2 px-3 py-1.5 rounded"
            style={{
              background: 'rgba(1,9,22,0.88)',
              backdropFilter: 'blur(16px)',
              border: `1px solid ${isPlayback ? accentColor + '60' : 'rgba(255,255,255,0.1)'}`,
              boxShadow: isPlayback ? `0 0 12px ${accentColor}30` : 'none',
            }}
          >
            <History size={11} style={{ color: isPlayback ? accentColor : 'rgba(255,255,255,0.4)' }} />
            <span
              className="text-[9px] font-mono font-bold tracking-widest"
              style={{ color: isPlayback ? accentColor : 'rgba(255,255,255,0.5)' }}
            >
              {isPlayback
                ? `PLAYBACK ${playbackIndex! + 1}/${snapshots.length}`
                : `${snapshots.length} SNAPSHOT${snapshots.length !== 1 ? 'S' : ''}`}
            </span>
            {isPlayback && (
              <span
                className="w-1.5 h-1.5 rounded-full"
                style={{ background: accentColor, animation: 'pulse-glow 1.5s ease-in-out infinite' }}
              />
            )}
          </motion.button>
        ) : (
          <motion.div
            key="expanded"
            initial={{ opacity: 0, y: 16, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.97 }}
            className="rounded overflow-hidden"
            style={{
              background: 'linear-gradient(145deg, rgba(1,9,22,0.94), rgba(2,14,30,0.92))',
              backdropFilter: 'blur(24px)',
              border: `1px solid ${accentColor}25`,
              boxShadow: `0 4px 32px rgba(0,0,0,0.5), 0 0 16px ${accentColor}10`,
            }}
          >
            {/* Header */}
            <div
              className="flex items-center justify-between px-3 py-2"
              style={{ borderBottom: `1px solid rgba(255,255,255,0.06)` }}
            >
              <div className="flex items-center gap-2">
                <History size={11} style={{ color: accentColor }} />
                <span className="text-[9px] font-mono font-bold tracking-widest" style={{ color: accentColor }}>
                  SNAPSHOTS
                </span>
              </div>
              <div className="flex items-center gap-2">
                {/* Save */}
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="flex items-center gap-1 px-2 py-0.5 rounded text-[9px] font-mono font-bold transition-all hover:opacity-80 disabled:opacity-40"
                  style={{
                    background: `${accentColor}15`,
                    border: `1px solid ${accentColor}40`,
                    color: accentColor,
                  }}
                  title="Save current state as snapshot"
                >
                  <Camera size={9} />
                  {saving ? 'SAVING…' : 'SAVE'}
                </button>
                {/* Close */}
                <button
                  onClick={() => setIsExpanded(false)}
                  className="text-foreground/30 hover:text-foreground/70 text-[10px] font-mono"
                >
                  ✕
                </button>
              </div>
            </div>

            {/* Playback controls */}
            {isPlayback && (
              <div
                className="flex items-center gap-2 px-3 py-2"
                style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}
              >
                <button onClick={() => handleStep(-1)} disabled={playbackIndex === 0}
                  className="p-1 rounded hover:bg-white/10 disabled:opacity-30 transition-all"
                  style={{ color: accentColor }}
                >
                  <ChevronLeft size={13} />
                </button>
                <div className="flex-1">
                  <input
                    type="range"
                    min={0}
                    max={Math.max(0, snapshots.length - 1)}
                    value={playbackIndex}
                    onChange={(e) => handleSelectSnapshot(Number(e.target.value))}
                    className="w-full h-1 rounded appearance-none cursor-pointer"
                    style={{ accentColor }}
                  />
                </div>
                <button onClick={() => handleStep(1)} disabled={playbackIndex === snapshots.length - 1}
                  className="p-1 rounded hover:bg-white/10 disabled:opacity-30 transition-all"
                  style={{ color: accentColor }}
                >
                  <ChevronRight size={13} />
                </button>
                <button
                  onClick={handleLive}
                  className="flex items-center gap-1 px-2 py-0.5 rounded text-[9px] font-mono font-bold"
                  style={{
                    background: 'rgba(52,211,153,0.15)',
                    border: '1px solid rgba(52,211,153,0.4)',
                    color: '#34d399',
                  }}
                >
                  <Play size={9} />
                  LIVE
                </button>
              </div>
            )}

            {/* Snapshot list */}
            <div className="max-h-48 overflow-y-auto scrollbar-hud">
              {snapshots.length === 0 && (
                <p className="text-[9px] font-mono text-foreground/30 text-center py-4">
                  No snapshots yet. Save one.
                </p>
              )}
              {[...snapshots].reverse().map((meta, reversedIdx) => {
                const idx = snapshots.length - 1 - reversedIdx;
                const isActive = playbackIndex === idx;
                return (
                  <button
                    key={meta.id}
                    onClick={() => handleSelectSnapshot(idx)}
                    className="w-full flex items-center gap-2 px-3 py-1.5 hover:bg-white/5 text-left transition-all group"
                    style={{
                      background: isActive ? `${accentColor}10` : undefined,
                      borderLeft: isActive ? `2px solid ${accentColor}` : '2px solid transparent',
                    }}
                  >
                    <Square
                      size={8}
                      style={{ color: isActive ? accentColor : 'rgba(255,255,255,0.3)', fill: isActive ? accentColor : 'transparent' }}
                    />
                    <div className="flex-1 min-w-0">
                      <div className="text-[9px] font-mono font-bold truncate"
                        style={{ color: isActive ? accentColor : '#94a3b8' }}>
                        {meta.label}
                      </div>
                      <div className="text-[8px] font-mono text-foreground/30">
                        {meta.eventCount} events · {meta.mode.toUpperCase()}
                      </div>
                    </div>
                    <button
                      onClick={(e) => { e.stopPropagation(); handleDelete(idx, meta.id); }}
                      className="opacity-0 group-hover:opacity-100 transition-opacity text-foreground/30 hover:text-red-400"
                    >
                      <Trash2 size={10} />
                    </button>
                  </button>
                );
              })}
            </div>

            {/* Loaded snapshot preview */}
            {loadedData && (
              <div
                className="px-3 py-2 text-[9px] font-mono"
                style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}
              >
                <span style={{ color: accentColor }}>VIEWING SNAPSHOT</span>
                <span className="ml-2 text-foreground/40">
                  {loadedData.events.length} events · {new Date(loadedData.createdAt).toISOString().slice(0, 19)} UTC
                </span>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
