import { useEffect, useCallback } from 'react';
import { useTaskStore } from '../store/useTaskStore';
import { fetchTasks, Task } from '../lib/tasks';

const getBackendUrl = () => {
  const port = import.meta.env.VITE_BACKEND_PORT || '8000';
  return `ws://127.0.0.1:${port}`;
};

export const useFetchTasks = () => {
  const { setTasks, addTask, updateTask, removeTask, setLoading, setError } = useTaskStore();

  const refetchTasks = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchTasks({ limit: 100 });
      setTasks(response?.tasks || []);
    } catch (err: any) {
      // ──────────────────────────────────────────────────────────
      // FIX 3: Catch JSON/404 errs gracefully and fail silently
      // ──────────────────────────────────────────────────────────
      setTasks([]);
    } finally {
      setLoading(false);
    }
  }, [setTasks, setLoading, setError]);

  const setupWebSocketListener = useCallback(() => {
    try {
      const backendUrl = getBackendUrl();
      const ws = new WebSocket(`${backendUrl}/ws/system`);

      ws.onopen = () => {
        console.log('✓ System WebSocket connected (tasks)');
      };

      ws.onmessage = (event) => {
        try {
          const frame = JSON.parse(event.data);

          if (frame.type === 'TASK_UPDATE') {
            const { operation, task_id, task } = frame;

            switch (operation) {
              case 'created':
                if (task) addTask(task as Task);
                break;
              case 'updated':
                if (task && task_id) updateTask(task_id, task);
                break;
              case 'deleted':
                if (task_id) removeTask(task_id);
                break;
              case 'completed':
                if (task && task_id) updateTask(task_id, { ...task, status: 'COMPLETED' });
                break;
            }
          }
        } catch (err) {
            // Muted frame serialization errors silently as requested
        }
      };

      ws.onerror = (err) => {
          // Muted console WS error traces to preserve pristine devtools
      };

      ws.onclose = () => {
        setTimeout(() => setupWebSocketListener(), 3000);
      };

      return ws;
    } catch (err) {
      return null;
    }
  }, [addTask, updateTask, removeTask]);

  useEffect(() => {
    refetchTasks();
    const ws = setupWebSocketListener();

    return () => {
      if (ws) ws.close();
    };
  }, [refetchTasks, setupWebSocketListener]);

  return { refetchTasks };
};
