/**
 * CaseDrawer — Investigation mode: click an event → open a case,
 * add notes, link related events, set status, track over time.
 *
 * Cases are persisted via Zustand persist middleware.
 * Slides in from the right edge as a full-height drawer.
 */
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FolderOpen, X, Plus, ChevronDown, ChevronUp, Trash2,
  Link, CheckCircle, Eye, Archive,
} from 'lucide-react';
import { useMonitorStore, type InvestigationCase } from '@/store/useMonitorStore';

const STATUS_COLORS: Record<InvestigationCase['status'], string> = {
  open:       '#f87171',
  monitoring: '#fbbf24',
  closed:     '#64748b',
};

const STATUS_ICONS: Record<InvestigationCase['status'], typeof CheckCircle> = {
  open:       CheckCircle,
  monitoring: Eye,
  closed:     Archive,
};

const SEV_COLORS: Record<string, string> = {
  critical: '#f87171',
  high:     '#fb923c',
  medium:   '#fbbf24',
  low:      '#34d399',
};

interface CaseDrawerProps {
  accentColor?: string;
}

export const CaseDrawer = ({ accentColor = '#00f5ff' }: CaseDrawerProps) => {
  const caseDrawerOpen    = useMonitorStore((s) => s.caseDrawerOpen);
  const toggleCaseDrawer  = useMonitorStore((s) => s.toggleCaseDrawer);
  const cases             = useMonitorStore((s) => s.cases);
  const removeCase        = useMonitorStore((s) => s.removeCase);
  const addCaseNote       = useMonitorStore((s) => s.addCaseNote);
  const updateCaseStatus  = useMonitorStore((s) => s.updateCaseStatus);

  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [noteInput,  setNoteInput]  = useState<Record<string, string>>({});

  const handleAddNote = (caseId: string) => {
    const note = (noteInput[caseId] || '').trim();
    if (!note) return;
    addCaseNote(caseId, note);
    setNoteInput((prev) => ({ ...prev, [caseId]: '' }));
  };

  const cycleStatus = (c: InvestigationCase) => {
    const cycle: InvestigationCase['status'][] = ['open', 'monitoring', 'closed'];
    const next = cycle[(cycle.indexOf(c.status) + 1) % cycle.length];
    updateCaseStatus(c.id, next);
  };

  const openCount = cases.filter((c) => c.status === 'open').length;

  return (
    <>
      {/* ── Floating trigger button ───────────────────────────────────────── */}
      <motion.button
        onClick={toggleCaseDrawer}
        className="fixed right-3 top-1/2 -translate-y-1/2 z-50 flex flex-col items-center gap-1.5 px-1.5 py-3 rounded pointer-events-auto"
        style={{
          background: 'rgba(1,9,22,0.88)',
          backdropFilter: 'blur(16px)',
          border: `1px solid ${caseDrawerOpen ? accentColor + '50' : 'rgba(255,255,255,0.1)'}`,
          boxShadow: caseDrawerOpen ? `0 0 16px ${accentColor}25` : 'none',
          writingMode: 'vertical-rl',
        }}
        whileHover={{ scale: 1.05 }}
        title="Toggle Case Drawer"
      >
        <FolderOpen size={11} style={{ color: accentColor }} />
        <span
          className="text-[8px] font-mono font-bold tracking-widest"
          style={{ color: `${accentColor}90`, writingMode: 'vertical-rl' }}
        >
          CASES
        </span>
        {openCount > 0 && (
          <span
            className="w-4 h-4 rounded-full text-[8px] font-mono font-bold flex items-center justify-center"
            style={{ background: accentColor, color: '#010812' }}
          >
            {openCount}
          </span>
        )}
      </motion.button>

      {/* ── Slide-in drawer ───────────────────────────────────────────────── */}
      <AnimatePresence>
        {caseDrawerOpen && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-40"
              style={{ background: 'rgba(0,0,0,0.3)' }}
              onClick={toggleCaseDrawer}
            />

            <motion.div
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', stiffness: 300, damping: 32 }}
              className="fixed top-0 right-0 h-full z-50 pointer-events-auto flex flex-col"
              style={{
                width: '22rem',
                background: 'linear-gradient(180deg, rgba(1,9,22,0.98) 0%, rgba(2,14,30,0.97) 100%)',
                backdropFilter: 'blur(32px)',
                borderLeft: `1px solid ${accentColor}25`,
                boxShadow: `-8px 0 48px rgba(0,0,0,0.6), -2px 0 16px ${accentColor}10`,
              }}
            >
              {/* Drawer header */}
              <div
                className="flex items-center justify-between px-4 py-3 shrink-0"
                style={{ borderBottom: `1px solid rgba(255,255,255,0.06)` }}
              >
                <div className="flex items-center gap-2">
                  <FolderOpen size={14} style={{ color: accentColor }} />
                  <span className="text-[11px] font-mono font-bold tracking-widest" style={{ color: accentColor }}>
                    INVESTIGATION CASES
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-[9px] font-mono text-foreground/40">
                    {cases.length} case{cases.length !== 1 ? 's' : ''}
                  </span>
                  <button onClick={toggleCaseDrawer}
                    className="text-foreground/40 hover:text-foreground/80 transition-colors">
                    <X size={14} />
                  </button>
                </div>
              </div>

              {/* Case list */}
              <div className="flex-1 overflow-y-auto scrollbar-hud p-3 space-y-2">
                {cases.length === 0 && (
                  <div className="text-center py-12">
                    <FolderOpen size={32} className="mx-auto mb-3 opacity-20" style={{ color: accentColor }} />
                    <p className="text-[10px] font-mono text-foreground/30">No cases open.</p>
                    <p className="text-[9px] font-mono text-foreground/20 mt-1">
                      Click an event on the map or in<br />a panel to start an investigation.
                    </p>
                  </div>
                )}

                {cases.map((c) => {
                  const isExpanded = expandedId === c.id;
                  const StatusIcon = STATUS_ICONS[c.status];

                  return (
                    <div
                      key={c.id}
                      className="rounded overflow-hidden"
                      style={{
                        background: 'rgba(255,255,255,0.025)',
                        border: `1px solid ${SEV_COLORS[c.severity] || accentColor}20`,
                      }}
                    >
                      {/* Case header */}
                      <div className="flex items-start gap-2 p-2.5">
                        <span
                          className="w-0.5 self-stretch rounded-full shrink-0"
                          style={{ background: SEV_COLORS[c.severity] || accentColor }}
                        />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-1.5 mb-1">
                            {/* Status cycle button */}
                            <button
                              onClick={() => cycleStatus(c)}
                              className="flex items-center gap-1 px-1.5 py-0.5 rounded text-[7px] font-mono font-bold transition-all hover:opacity-80"
                              style={{
                                background: `${STATUS_COLORS[c.status]}15`,
                                border: `1px solid ${STATUS_COLORS[c.status]}40`,
                                color: STATUS_COLORS[c.status],
                              }}
                            >
                              <StatusIcon size={8} />
                              {c.status.toUpperCase()}
                            </button>
                            <span className="text-[7px] font-mono text-foreground/30 ml-auto">
                              {c.category.toUpperCase()}
                            </span>
                          </div>
                          <p className="text-[10px] font-mono font-bold text-foreground/90 leading-tight">
                            {c.title}
                          </p>
                          <p className="text-[8px] font-mono text-foreground/40 mt-0.5">
                            {new Date(c.createdAt).toISOString().slice(0, 16).replace('T', ' ')} UTC
                            {c.notes.length > 0 && ` · ${c.notes.length} note${c.notes.length > 1 ? 's' : ''}`}
                            {c.linkedEventIds.length > 0 && ` · ${c.linkedEventIds.length} linked`}
                          </p>
                        </div>
                        {/* Expand / delete */}
                        <div className="flex items-center gap-1 shrink-0">
                          <button
                            onClick={() => setExpandedId(isExpanded ? null : c.id)}
                            className="p-1 rounded hover:bg-white/10 text-foreground/40 hover:text-foreground/70 transition-all"
                          >
                            {isExpanded ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
                          </button>
                          <button
                            onClick={() => removeCase(c.id)}
                            className="p-1 rounded hover:bg-red-900/30 text-foreground/30 hover:text-red-400 transition-all"
                          >
                            <Trash2 size={11} />
                          </button>
                        </div>
                      </div>

                      {/* Expanded: notes + add note */}
                      <AnimatePresence>
                        {isExpanded && (
                          <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: 'auto', opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}
                          >
                            {/* Notes */}
                            <div className="px-3 py-2 space-y-1.5">
                              {c.notes.length === 0 && (
                                <p className="text-[8px] font-mono text-foreground/25">No notes yet.</p>
                              )}
                              {c.notes.map((n) => (
                                <div key={n.id}
                                  className="p-1.5 rounded"
                                  style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.06)' }}>
                                  <p className="text-[9px] font-mono text-foreground/70">{n.content}</p>
                                  <p className="text-[7px] font-mono text-foreground/25 mt-0.5">
                                    {new Date(n.createdAt).toISOString().slice(11, 16)} UTC
                                  </p>
                                </div>
                              ))}
                            </div>

                            {/* Add note */}
                            <div className="px-3 pb-2.5 flex gap-1.5">
                              <input
                                type="text"
                                value={noteInput[c.id] || ''}
                                onChange={(e) => setNoteInput((p) => ({ ...p, [c.id]: e.target.value }))}
                                onKeyDown={(e) => { if (e.key === 'Enter') handleAddNote(c.id); }}
                                placeholder="Add investigation note…"
                                className="flex-1 px-2 py-1 text-[9px] font-mono rounded outline-none"
                                style={{
                                  background: 'rgba(255,255,255,0.05)',
                                  border: `1px solid ${accentColor}20`,
                                  color: '#e2e8f0',
                                  caretColor: accentColor,
                                }}
                              />
                              <button
                                onClick={() => handleAddNote(c.id)}
                                className="p-1 rounded transition-all hover:opacity-80"
                                style={{
                                  background: `${accentColor}15`,
                                  border: `1px solid ${accentColor}40`,
                                  color: accentColor,
                                }}
                              >
                                <Plus size={11} />
                              </button>
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>
                  );
                })}
              </div>

              {/* Footer */}
              <div
                className="px-4 py-2 shrink-0"
                style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}
              >
                <p className="text-[8px] font-mono text-foreground/25">
                  Cases persist across sessions · stored locally
                </p>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
};
