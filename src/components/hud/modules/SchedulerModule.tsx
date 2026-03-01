import { useState } from 'react';
import { Clock, Plus, Trash2, Bell, CheckCircle, AlertTriangle, AlertOctagon, Loader2, History, Calendar } from 'lucide-react';
import { useScheduler } from '@/hooks/useScheduler';
import type { CreateReminderPayload, Reminder } from '@/hooks/useScheduler';

const SEVERITY_CFG = {
  info:     { color: '#00f5ff', icon: Bell,           label: 'INFO'     },
  warning:  { color: '#ff9f0a', icon: AlertTriangle,  label: 'WARNING'  },
  critical: { color: '#ff453a', icon: AlertOctagon,   label: 'CRITICAL' },
};

function ReminderCard({ reminder, onDelete, onToggle }: {
  reminder: Reminder;
  onDelete: (id: string) => void;
  onToggle: (id: string, enabled: boolean) => void;
}) {
  const sev = SEVERITY_CFG[reminder.severity];
  const SevIcon = sev.icon;

  const formatTime = (iso: string | null) => {
    if (!iso) return '—';
    return new Date(iso).toLocaleString();
  };

  const triggerLabel = reminder.fire_at
    ? `📅 ${formatTime(reminder.fire_at)}`
    : reminder.cron
    ? `⚙️ CRON: ${reminder.cron}`
    : reminder.interval_seconds
    ? `🔁 Every ${reminder.interval_seconds}s`
    : '?';

  return (
    <div
      className={`hud-panel rounded p-3 flex flex-col gap-2 transition-all ${!reminder.enabled ? 'opacity-50' : ''}`}
      style={{ borderLeft: `3px solid ${sev.color}` }}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <SevIcon size={12} style={{ color: sev.color, flexShrink: 0 }} />
          <div className="min-w-0">
            <div className="font-orbitron text-[10px] text-hud-cyan truncate">{reminder.title}</div>
            <div className="font-mono-tech text-[8px] text-hud-cyan/40 mt-0.5">{triggerLabel}</div>
          </div>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          <button
            onClick={() => onToggle(reminder.id, !reminder.enabled)}
            className={`font-orbitron text-[7px] px-1.5 py-0.5 rounded border transition-all ${
              reminder.enabled
                ? 'border-hud-green/40 text-hud-green/70 hover:border-hud-green'
                : 'border-hud-cyan/20 text-hud-cyan/30 hover:border-hud-cyan/50'
            }`}
          >
            {reminder.enabled ? '● ON' : '○ OFF'}
          </button>
          <button
            onClick={() => onDelete(reminder.id)}
            className="text-hud-red/40 hover:text-hud-red transition-colors p-0.5"
          >
            <Trash2 size={10} />
          </button>
        </div>
      </div>

      {reminder.body && (
        <div className="font-mono-tech text-[8px] text-hud-cyan/50 leading-relaxed">
          {reminder.body}
        </div>
      )}

      <div className="flex items-center gap-3">
        <span className="font-mono-tech text-[7px] text-hud-cyan/30">
          Fired: <span className="text-hud-cyan/50">{reminder.fired_count}×</span>
        </span>
        {reminder.last_fired && (
          <span className="font-mono-tech text-[7px] text-hud-cyan/30">
            Last: <span className="text-hud-cyan/50">{formatTime(reminder.last_fired)}</span>
          </span>
        )}
        {reminder.repeat && (
          <span className="font-orbitron text-[6px] text-hud-amber/60 border border-hud-amber/30 px-1 rounded">REPEAT</span>
        )}
      </div>
    </div>
  );
}

function CreateForm({ onSubmit, isCreating }: { onSubmit: (p: CreateReminderPayload) => void; isCreating: boolean }) {
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [fireAt, setFireAt] = useState('');
  const [cron, setCron] = useState('');
  const [intervalSec, setIntervalSec] = useState('');
  const [severity, setSeverity] = useState<'info' | 'warning' | 'critical'>('info');
  const [repeat, setRepeat] = useState(false);
  const [open, setOpen] = useState(false);

  const submit = () => {
    if (!title.trim()) return;
    const payload: CreateReminderPayload = {
      title: title.trim(),
      body: body.trim(),
      severity,
      repeat,
    };
    if (fireAt) payload.fire_at = new Date(fireAt).toISOString();
    if (cron) payload.cron = cron;
    if (intervalSec) payload.interval_seconds = parseInt(intervalSec, 10);

    onSubmit(payload);
    setTitle(''); setBody(''); setFireAt(''); setCron(''); setIntervalSec('');
    setOpen(false);
  };

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="w-full flex items-center justify-center gap-2 py-2.5 rounded border border-dashed border-hud-cyan/30 text-hud-cyan/50 hover:border-hud-cyan/60 hover:text-hud-cyan transition-all font-orbitron text-[9px]"
      >
        <Plus size={12} /> ADD REMINDER
      </button>
    );
  }

  return (
    <div className="hud-panel rounded p-3 flex flex-col gap-2">
      <div className="font-orbitron text-[9px] text-hud-cyan/70 mb-1 flex items-center gap-1">
        <Plus size={10} /> NEW REMINDER
      </div>

      <input
        value={title}
        onChange={e => setTitle(e.target.value)}
        placeholder="TITLE *"
        className="bg-transparent border border-hud-cyan/20 rounded px-2 py-1 font-mono-tech text-[9px] text-hud-cyan placeholder:text-hud-cyan/30 outline-none focus:border-hud-cyan/50"
      />
      <input
        value={body}
        onChange={e => setBody(e.target.value)}
        placeholder="MESSAGE (optional)"
        className="bg-transparent border border-hud-cyan/20 rounded px-2 py-1 font-mono-tech text-[9px] text-hud-cyan placeholder:text-hud-cyan/30 outline-none focus:border-hud-cyan/50"
      />

      <div className="grid grid-cols-3 gap-2">
        <div className="flex flex-col gap-1">
          <label className="font-orbitron text-[7px] text-hud-cyan/40">FIRE AT</label>
          <input
            type="datetime-local"
            value={fireAt}
            onChange={e => setFireAt(e.target.value)}
            className="bg-transparent border border-hud-cyan/20 rounded px-2 py-1 font-mono-tech text-[8px] text-hud-cyan outline-none focus:border-hud-cyan/50 [color-scheme:dark]"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="font-orbitron text-[7px] text-hud-cyan/40">CRON</label>
          <input
            value={cron}
            onChange={e => setCron(e.target.value)}
            placeholder="0 9 * * *"
            className="bg-transparent border border-hud-cyan/20 rounded px-2 py-1 font-mono-tech text-[8px] text-hud-cyan placeholder:text-hud-cyan/30 outline-none focus:border-hud-cyan/50"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="font-orbitron text-[7px] text-hud-cyan/40">EVERY (sec)</label>
          <input
            type="number"
            value={intervalSec}
            onChange={e => setIntervalSec(e.target.value)}
            placeholder="3600"
            className="bg-transparent border border-hud-cyan/20 rounded px-2 py-1 font-mono-tech text-[8px] text-hud-cyan placeholder:text-hud-cyan/30 outline-none focus:border-hud-cyan/50"
          />
        </div>
      </div>

      <div className="flex items-center gap-3">
        <div className="flex gap-1">
          {(['info', 'warning', 'critical'] as const).map(s => {
            const cfg = SEVERITY_CFG[s];
            return (
              <button
                key={s}
                onClick={() => setSeverity(s)}
                className="font-orbitron text-[7px] px-1.5 py-0.5 rounded border transition-all"
                style={{
                  borderColor: severity === s ? cfg.color : `${cfg.color}40`,
                  color: severity === s ? cfg.color : `${cfg.color}60`,
                  background: severity === s ? `${cfg.color}18` : 'transparent',
                }}
              >
                {cfg.label}
              </button>
            );
          })}
        </div>
        <label className="flex items-center gap-1 cursor-pointer">
          <input
            type="checkbox"
            checked={repeat}
            onChange={e => setRepeat(e.target.checked)}
            className="accent-hud-cyan w-3 h-3"
          />
          <span className="font-orbitron text-[8px] text-hud-cyan/50">REPEAT</span>
        </label>
      </div>

      <div className="flex gap-2 mt-1">
        <button
          onClick={submit}
          disabled={!title.trim() || isCreating}
          className="flex-1 flex items-center justify-center gap-1 font-orbitron text-[8px] px-2 py-1.5 rounded border border-hud-cyan/40 text-hud-cyan hover:bg-hud-cyan/10 transition-all disabled:opacity-40"
        >
          {isCreating ? <Loader2 size={10} className="animate-spin" /> : <CheckCircle size={10} />}
          CREATE
        </button>
        <button
          onClick={() => setOpen(false)}
          className="font-orbitron text-[8px] px-3 py-1.5 rounded border border-hud-red/30 text-hud-red/60 hover:border-hud-red/60 transition-all"
        >
          CANCEL
        </button>
      </div>
    </div>
  );
}

export default function SchedulerModule() {
  const { reminders, status, history, isLoading, createReminder, deleteReminder, toggleReminder, isCreating } = useScheduler();
  const [tab, setTab] = useState<'reminders' | 'history'>('reminders');

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="px-4 pt-3 pb-2 border-b border-hud-cyan/20 shrink-0">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Clock size={14} className="text-hud-cyan" />
            <span className="font-orbitron text-xs tracking-widest neon-text">SCHEDULER & REMINDERS</span>
            {isLoading && <Loader2 size={12} className="text-hud-cyan/50 animate-spin" />}
          </div>
          {status && (
            <div className={`flex items-center gap-1 font-orbitron text-[8px] px-2 py-0.5 rounded border ${status.running ? 'border-hud-green/40 text-hud-green' : 'border-hud-red/40 text-hud-red'}`}>
              <div className={`w-1.5 h-1.5 rounded-full ${status.running ? 'bg-hud-green animate-pulse' : 'bg-hud-red'}`} />
              {status.running ? 'RUNNING' : 'STOPPED'} · {status.job_count} JOBS
            </div>
          )}
        </div>

        {/* Tabs */}
        <div className="flex gap-1">
          {(['reminders', 'history'] as const).map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`flex items-center gap-1 font-orbitron text-[8px] px-2 py-1 rounded border transition-all ${
                tab === t
                  ? 'border-hud-cyan text-hud-cyan bg-hud-cyan/10'
                  : 'border-hud-cyan/20 text-hud-cyan/40 hover:border-hud-cyan/40'
              }`}
            >
              {t === 'reminders' ? <Bell size={9} /> : <History size={9} />}
              {t.toUpperCase()}
              {t === 'reminders' && <span className="text-hud-cyan/60">({reminders.length})</span>}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto scrollbar-hud p-3 flex flex-col gap-2">
        {tab === 'reminders' && (
          <>
            <CreateForm onSubmit={createReminder} isCreating={isCreating} />
            {reminders.length === 0 && !isLoading && (
              <div className="flex flex-col items-center justify-center h-32 text-hud-cyan/30">
                <Calendar size={24} className="mb-2 opacity-40" />
                <span className="font-orbitron text-[9px]">NO REMINDERS SET</span>
              </div>
            )}
            {reminders.map(r => (
              <ReminderCard
                key={r.id}
                reminder={r}
                onDelete={deleteReminder}
                onToggle={toggleReminder}
              />
            ))}
          </>
        )}

        {tab === 'history' && (
          <>
            {history.length === 0 ? (
              <div className="flex items-center justify-center h-32 text-hud-cyan/30">
                <span className="font-orbitron text-[9px]">NO HISTORY YET</span>
              </div>
            ) : (
              history.map((h, i) => (
                <div key={i} className="hud-panel rounded p-2 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <CheckCircle size={10} className="text-hud-green/60" />
                    <span className="font-orbitron text-[9px] text-hud-cyan">{h.title}</span>
                  </div>
                  <span className="font-mono-tech text-[8px] text-hud-cyan/40">
                    {new Date(h.fired_at).toLocaleString()}
                  </span>
                </div>
              ))
            )}
          </>
        )}
      </div>
    </div>
  );
}
