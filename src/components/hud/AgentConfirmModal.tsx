/**
 * AgentConfirmModal
 * ─────────────────────────────────────────────────────────────────────────────
 * Full-screen confirmation overlay triggered when the Desktop Agent sends a
 * CONFIRM_TOOL frame via /ws/system (risk_level: HIGH actions).
 *
 * On CONFIRM → POST http://127.0.0.1:7700/agent/confirm/{token}
 * On CANCEL  → POST http://127.0.0.1:7700/agent/cancel/{token}
 *
 * Displayed result is fed back as a TOOL_RESULT into useToolActivityStore.
 */

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Shield, Terminal, AlertTriangle, CheckCircle, XCircle } from 'lucide-react';
import { useToolActivityStore } from '@/store/useToolActivityStore';
import { useAlertStore } from '@/store/useAlertStore';

const AGENT_BASE = 'http://127.0.0.1:7700';

export interface ConfirmRequest {
  token: string;
  tool: string;
  command: string;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  description?: string;
  arguments?: Record<string, unknown>;
}

interface AgentConfirmModalProps {
  request: ConfirmRequest | null;
  onClose: () => void;
}

const RISK_STYLES: Record<string, { color: string; border: string; label: string }> = {
  LOW:      { color: '#30d158', border: 'border-hud-green/40', label: 'LOW RISK' },
  MEDIUM:   { color: '#ff9f0a', border: 'border-hud-amber/50', label: 'MEDIUM RISK' },
  HIGH:     { color: '#ff6b35', border: 'border-hud-amber/70', label: 'HIGH RISK' },
  CRITICAL: { color: '#ff2d55', border: 'border-hud-red/70', label: 'CRITICAL RISK' },
};

export default function AgentConfirmModal({ request, onClose }: AgentConfirmModalProps) {
  const [status, setStatus] = useState<'idle' | 'confirming' | 'cancelling' | 'done'>('idle');
  const [result, setResult] = useState<string | null>(null);
  const { addExecute, addResult } = useToolActivityStore();
  const { addAlert } = useAlertStore();

  // Auto-close after showing result
  useEffect(() => {
    if (status === 'done') {
      const t = setTimeout(onClose, 2_500);
      return () => clearTimeout(t);
    }
  }, [status, onClose]);

  if (!request) return null;

  const risk = RISK_STYLES[request.risk_level] ?? RISK_STYLES.HIGH;

  const handleConfirm = async () => {
    setStatus('confirming');
    addExecute(request.tool, request.arguments);
    try {
      const res = await fetch(`${AGENT_BASE}/agent/confirm/${request.token}`, { method: 'POST' });
      const data = await res.json().catch(() => ({}));
      addResult(request.tool, 'success', data.output ?? 'Command dispatched');
      addAlert({
        severity: 'info',
        title: `Tool executed: ${request.tool}`,
        body: data.output ?? '',
        source: 'desktop-agent',
        ts: Date.now(),
      });
      setResult('✓ Command dispatched successfully');
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Agent unreachable';
      addResult(request.tool, 'error', undefined, msg);
      addAlert({
        severity: 'warning',
        title: `Tool failed: ${request.tool}`,
        body: msg,
        source: 'desktop-agent',
        ts: Date.now(),
      });
      setResult(`⚠ ${msg}`);
    }
    setStatus('done');
  };

  const handleCancel = async () => {
    setStatus('cancelling');
    try {
      await fetch(`${AGENT_BASE}/agent/cancel/${request.token}`, { method: 'POST' });
    } catch { /* best-effort */ }
    addAlert({
      severity: 'info',
      title: `Tool cancelled: ${request.tool}`,
      body: request.description ?? '',
      source: 'desktop-agent',
      ts: Date.now(),
    });
    setResult('◌ Action cancelled by operator');
    setStatus('done');
  };

  return (
    <AnimatePresence>
      {/* Backdrop */}
      <motion.div
        key="backdrop"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-[200] bg-black/70 backdrop-blur-sm"
        onClick={status === 'idle' ? handleCancel : undefined}
      />

      {/* Modal */}
      <motion.div
        key="modal"
        initial={{ scale: 0.85, opacity: 0, y: -20 }}
        animate={{ scale: 1, opacity: 1, y: 0 }}
        exit={{ scale: 0.9, opacity: 0 }}
        transition={{ type: 'spring', stiffness: 350, damping: 30 }}
        className={`fixed z-[201] top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-lg rounded-lg border ${risk.border} hud-panel overflow-hidden`}
        style={{ boxShadow: `0 0 60px ${risk.color}30, 0 0 120px ${risk.color}10` }}
      >
        {/* Risk accent bar */}
        <div className="h-1 w-full" style={{ background: risk.color, boxShadow: `0 0 10px ${risk.color}` }} />

        <div className="p-5">
          {/* Header */}
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-full border-2 flex items-center justify-center"
              style={{ borderColor: risk.color, boxShadow: `0 0 20px ${risk.color}40` }}>
              <Shield size={18} style={{ color: risk.color }} />
            </div>
            <div>
              <div className="font-orbitron text-sm font-bold" style={{ color: risk.color }}>
                AGENT AUTHORIZATION REQUEST
              </div>
              <div className="font-mono-tech text-[9px] text-white/40 uppercase tracking-widest">
                {risk.label} · Desktop Agent
              </div>
            </div>
          </div>

          {/* Risk badge */}
          <div className="flex items-center gap-2 mb-4 p-2 rounded border"
            style={{ borderColor: `${risk.color}30`, background: `${risk.color}08` }}>
            <AlertTriangle size={12} style={{ color: risk.color }} />
            <span className="font-orbitron text-[9px] tracking-widest" style={{ color: risk.color }}>
              {risk.label}
            </span>
          </div>

          {/* Tool + command */}
          <div className="space-y-2 mb-5">
            <div>
              <div className="font-orbitron text-[8px] text-white/30 uppercase tracking-widest mb-1">Tool</div>
              <div className="font-mono-tech text-sm text-hud-cyan">{request.tool}</div>
            </div>

            <div>
              <div className="font-orbitron text-[8px] text-white/30 uppercase tracking-widest mb-1">
                <Terminal size={8} className="inline mr-1" />
                Command
              </div>
              <div
                className="rounded border border-hud-cyan/20 bg-black/60 px-3 py-2 font-mono-tech text-xs text-hud-cyan/80 break-all"
                style={{ textShadow: '0 0 8px hsl(186 100% 50% / 0.3)' }}
              >
                {request.command}
              </div>
            </div>

            {request.description && (
              <div>
                <div className="font-orbitron text-[8px] text-white/30 uppercase tracking-widest mb-1">Description</div>
                <div className="font-mono-tech text-[10px] text-white/50">{request.description}</div>
              </div>
            )}

            {request.arguments && Object.keys(request.arguments).length > 0 && (
              <div>
                <div className="font-orbitron text-[8px] text-white/30 uppercase tracking-widest mb-1">Arguments</div>
                <pre className="font-mono-tech text-[8px] text-hud-cyan/40 max-h-20 overflow-y-auto">
                  {JSON.stringify(request.arguments, null, 2)}
                </pre>
              </div>
            )}
          </div>

          {/* Result display */}
          <AnimatePresence>
            {result && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="mb-4 rounded border border-white/10 bg-white/5 px-3 py-2 font-mono-tech text-[10px] text-white/60"
              >
                {result}
              </motion.div>
            )}
          </AnimatePresence>

          {/* Action buttons */}
          {status === 'idle' && (
            <div className="flex gap-3">
              <button
                onClick={handleCancel}
                className="flex-1 hud-btn py-2.5 rounded border border-hud-red/40 font-orbitron text-[10px] tracking-widest text-hud-red/80 hover:bg-hud-red/10 hover:border-hud-red/70 transition-all flex items-center justify-center gap-2"
              >
                <XCircle size={12} />
                DENY
              </button>
              <button
                onClick={handleConfirm}
                className="flex-1 py-2.5 rounded border font-orbitron text-[10px] tracking-widest transition-all flex items-center justify-center gap-2"
                style={{
                  borderColor: risk.color,
                  color: risk.color,
                  background: `${risk.color}15`,
                }}
              >
                <CheckCircle size={12} />
                AUTHORIZE
              </button>
            </div>
          )}

          {(status === 'confirming' || status === 'cancelling') && (
            <div className="flex items-center justify-center gap-2 py-2 font-orbitron text-[10px] text-hud-cyan/60">
              <div className="w-3 h-3 border border-hud-cyan/60 border-t-transparent rounded-full animate-spin" />
              {status === 'confirming' ? 'SENDING TO AGENT...' : 'CANCELLING...'}
            </div>
          )}

          {status === 'done' && (
            <div className="text-center font-mono-tech text-[10px] text-white/40 py-1">
              Closing...
            </div>
          )}
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
