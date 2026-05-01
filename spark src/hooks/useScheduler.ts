import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

const API = 'http://localhost:8000';

export interface Reminder {
  id: string;
  title: string;
  body: string;
  fire_at: string | null;
  cron: string | null;
  interval_seconds: number | null;
  severity: 'info' | 'warning' | 'critical';
  enabled: boolean;
  repeat: boolean;
  created_at: string;
  fired_count: number;
  last_fired: string | null;
}

export interface CreateReminderPayload {
  title: string;
  body: string;
  fire_at?: string;
  cron?: string;
  interval_seconds?: number;
  severity?: 'info' | 'warning' | 'critical';
  repeat?: boolean;
}

export interface SchedulerStatus {
  running: boolean;
  job_count: number;
  reminder_count: number;
  thread_pool_size: number;
}

export function useScheduler() {
  const qc = useQueryClient();

  const { data: reminders = [], isLoading } = useQuery<Reminder[]>({
    queryKey: ['reminders'],
    queryFn: async () => {
      const res = await fetch(`${API}/api/scheduler/reminders`);
      if (!res.ok) throw new Error('Failed to fetch reminders');
      const data = await res.json();
      return data.reminders ?? [];
    },
    refetchInterval: 5000,
    retry: 2,
  });

  const { data: status } = useQuery<SchedulerStatus>({
    queryKey: ['scheduler-status'],
    queryFn: async () => {
      const res = await fetch(`${API}/api/scheduler/status`);
      if (!res.ok) throw new Error('Failed to fetch scheduler status');
      return res.json();
    },
    refetchInterval: 5000,
    retry: 2,
  });

  const { data: history = [] } = useQuery<Array<{ job_id: string; fired_at: string; title: string }>>({
    queryKey: ['scheduler-history'],
    queryFn: async () => {
      const res = await fetch(`${API}/api/scheduler/history`);
      if (!res.ok) throw new Error('Failed to fetch job history');
      const data = await res.json();
      return data.history ?? [];
    },
    refetchInterval: 10000,
    retry: 2,
  });

  const createMutation = useMutation({
    mutationFn: async (payload: CreateReminderPayload) => {
      const res = await fetch(`${API}/api/scheduler/reminders`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error('Create failed');
      return res.json();
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['reminders'] }),
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      const res = await fetch(`${API}/api/scheduler/reminders/${id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Delete failed');
      return res.json();
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['reminders'] }),
  });

  const toggleMutation = useMutation({
    mutationFn: async ({ id, enabled }: { id: string; enabled: boolean }) => {
      const res = await fetch(`${API}/api/scheduler/reminders/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled }),
      });
      if (!res.ok) throw new Error('Toggle failed');
      return res.json();
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['reminders'] }),
  });

  return {
    reminders,
    status,
    history,
    isLoading,
    createReminder: (payload: CreateReminderPayload) => createMutation.mutate(payload),
    deleteReminder: (id: string) => deleteMutation.mutate(id),
    toggleReminder: (id: string, enabled: boolean) => toggleMutation.mutate({ id, enabled }),
    isCreating: createMutation.isPending,
  };
}
