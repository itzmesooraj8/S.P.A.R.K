import { useEffect, useCallback } from 'react';
import { useTaskStore } from '../store/useTaskStore';
import { fetchTasks, Task } from '../lib/tasks';

const getBackendUrl = () => {
  const port = import.meta.env.VITE_BACKEND_PORT || '8000';
  return `ws://127.0.0.1:${port}`;
};

export const useFetchTasks = () => {
  const { setTasks, addTask, updateTask, removeTask, setLoading, setError } = useTaskStore();

  // Fetch tasks from backend on mount
  const refetchTasks = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchTasks({ limit: 100 });
      setTasks(response.tasks);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch tasks';
      setError(message);
      console.error('Failed to fetch tasks:', err);
    } finally {
      setLoading(false);
    }
  }, [setTasks, setLoading, setError]);

  // WebSocket listener for real-time task updates
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
          console.warn('Failed to parse WebSocket frame:', err);
        }
      };

      ws.onerror = (err) => {
        console.error('WebSocket error (tasks):', err);
      };

      ws.onclose = () => {
        console.log('✗ System WebSocket disconnected (tasks)');
        // Attempt reconnection after 3s
        setTimeout(() => setupWebSocketListener(), 3000);
      };

      return ws;
    } catch (err) {
      console.error('Failed to setup WebSocket:', err);
      return null;
    }
  }, [addTask, updateTask, removeTask]);

  // Setup on mount: fetch tasks and listen for updates
  useEffect(() => {
    refetchTasks();
    const ws = setupWebSocketListener();

    return () => {
      if (ws) ws.close();
    };
  }, [refetchTasks, setupWebSocketListener]);

  return { refetchTasks };
};
