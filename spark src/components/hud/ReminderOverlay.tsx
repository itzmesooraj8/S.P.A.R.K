import React, { useState, useEffect } from 'react';
import { useSparkStore } from '../../store/sparkStore';

export function ReminderOverlay() {
  const reminders = useSparkStore(state => state.reminders);
  const activeReminders = reminders.filter(r => r.active);
  const [dismissedIds, setDismissedIds] = useState<Set<string>>(new Set());

  const visibleReminders = activeReminders.filter(r => !dismissedIds.has(r.id));

  if (visibleReminders.length === 0) return null;

  return (
    <div className="fixed top-20 right-8 z-50 flex flex-col gap-4 max-w-sm pointer-events-none">
      {visibleReminders.map(reminder => (
        <div 
          key={reminder.id}
          className="hud-panel border-amber-500 bg-[#1a1200E6] p-4 flex flex-col shadow-[0_0_20px_rgba(255,176,0,0.3)] animate-pulse pointer-events-auto"
          style={{ animationDuration: '3s' }}
        >
          <div className="flex justify-between items-center mb-2">
            <span className="text-xs font-bold uppercase tracking-widest text-amber-500 flex items-center gap-2">
              <span className="w-2 h-2 bg-amber-500 rounded-full animate-ping"></span>
              ACTIVE REMINDER
            </span>
            <button 
              className="text-amber-500/50 hover:text-amber-400 text-sm font-mono"
              onClick={() => setDismissedIds(prev => new Set(prev).add(reminder.id))}
            >
              [DISMISS]
            </button>
          </div>
          
          <div className="font-mono text-amber-100 text-sm">
            {reminder.message}
          </div>
          
          <div className="mt-2 text-[10px] text-amber-500/60 font-mono text-right">
            DUE: {reminder.time}
          </div>
        </div>
      ))}
    </div>
  );
}
