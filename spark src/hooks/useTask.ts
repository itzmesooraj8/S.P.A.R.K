import { useState } from 'react';

export interface TaskResult {
  task_id?: string;
  goal: string;
  steps: string[];
  results: string[];
  status: 'queued' | 'pending' | 'running' | 'done' | 'blocked';
}

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000';

export function useTask() {
  const [task, setTask] = useState<TaskResult | null>(null);
  const [loading, setLoading] = useState(false);

  async function runTask(goal: string) {
    const trimmedGoal = goal.trim();
    if (!trimmedGoal || loading) return;

    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/task`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ goal: trimmedGoal }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      setTask({
        task_id: String(data.task_id ?? ''),
        goal: String(data.goal ?? trimmedGoal),
        steps: Array.isArray(data.steps) ? data.steps.map(String) : [],
        results: Array.isArray(data.results) ? data.results.map(String) : [],
        status: data.status === 'queued' || data.status === 'running' || data.status === 'done' || data.status === 'blocked'
          ? data.status
          : 'pending',
      });
    } finally {
      setLoading(false);
    }
  }

  return { task, loading, runTask };
}