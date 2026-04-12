import { useEffect, useCallback } from 'react';
import { useTaskStore } from '../store/useTaskStore';
import { fetchTasks, Task } from '../lib/tasks';
import { buildAuthedWsUrl } from '../lib/wsAuth';

type TaskUpdateOperation = 'created' | 'updated' | 'deleted' | 'completed';

interface TaskUpdateFrame {
  type?: string;
  operation?: string;
  task_id?: string;
  task?: Task;
  payload?: {
    operation?: string;
    task_id?: string;
    task?: Task;
  };
}

const normalizeTaskUpdate = (frame: TaskUpdateFrame): {
  operation: TaskUpdateOperation;
  taskId?: string;
  task?: Task;
} | null => {
  const source = frame.payload ?? frame;
  const operation = (source.operation || '').toLowerCase();
  if (!['created', 'updated', 'deleted', 'completed'].includes(operation)) {
    return null;
  }

  return {
    operation: operation as TaskUpdateOperation,
    taskId: source.task_id,
    task: source.task,
  };
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
      const ws = new WebSocket(buildAuthedWsUrl('/ws/system'));

      ws.onopen = () => {
        console.log('✓ System WebSocket connected (tasks)');
      };

      ws.onmessage = (event) => {
        try {
          const frame: TaskUpdateFrame = JSON.parse(event.data);

          if ((frame.type || '').toUpperCase() === 'TASK_UPDATE') {
            const normalized = normalizeTaskUpdate(frame);
            if (!normalized) {
              return;
            }

            const { operation, taskId, task } = normalized;

            switch (operation) {
              case 'created':
                if (task) addTask(task as Task);
                break;
              case 'updated':
                if (task && taskId) updateTask(taskId, task);
                break;
              case 'deleted':
                if (taskId) removeTask(taskId);
                break;
              case 'completed':
                if (task && taskId) updateTask(taskId, { ...task, status: 'COMPLETED' });
                break;
            }
          }
        } catch (err) {
          // Ignore malformed frames to keep HUD loop resilient.
        }
      };

      ws.onerror = (err) => {
        // Keep silent to avoid devtools noise during backend restarts.
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
