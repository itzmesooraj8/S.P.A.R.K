import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

export interface Task {
  id: string;
  title: string;
  description?: string;
  status: string;
  priority: number;
  due_date?: number;
  tags: string[];
  recurring?: string;
  created_at: number;
  updated_at: number;
  meta?: Record<string, any>;
}

export interface TaskStoreState {
  tasks: Task[];
  loading: boolean;
  error: string | null;

  // Actions
  addTask: (task: Task) => void;
  updateTask: (id: string, updates: Partial<Task>) => void;
  removeTask: (id: string) => void;
  setTasks: (tasks: Task[]) => void;
  clearCompleted: () => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;

  // Selectors
  getTaskById: (id: string) => Task | undefined;
  getTasksByStatus: (status: string) => Task[];
  getPendingCount: () => number;
  getCompletedTasks: () => Task[];
}

export const useTaskStore = create<TaskStoreState>()(
  persist(
    (set, get) => ({
      tasks: [],
      loading: false,
      error: null,

      addTask: (task: Task) =>
        set((state) => ({
          tasks: [...state.tasks, task],
        })),

      updateTask: (id: string, updates: Partial<Task>) =>
        set((state) => ({
          tasks: state.tasks.map((t) =>
            t.id === id ? { ...t, ...updates, updated_at: Date.now() / 1000 } : t
          ),
        })),

      removeTask: (id: string) =>
        set((state) => ({
          tasks: state.tasks.filter((t) => t.id !== id),
        })),

      setTasks: (tasks: Task[]) =>
        set(() => ({
          tasks,
        })),

      clearCompleted: () =>
        set((state) => ({
          tasks: state.tasks.filter((t) => t.status !== 'COMPLETED'),
        })),

      setLoading: (loading: boolean) =>
        set(() => ({
          loading,
        })),

      setError: (error: string | null) =>
        set(() => ({
          error,
        })),

      getTaskById: (id: string) => {
        const { tasks } = get();
        return tasks.find((t) => t.id === id);
      },

      getTasksByStatus: (status: string) => {
        const { tasks } = get();
        return tasks.filter((t) => t.status === status);
      },

      getPendingCount: () => {
        const { tasks } = get();
        return tasks.filter((t) => t.status === 'PENDING' || t.status === 'IN_PROGRESS').length;
      },

      getCompletedTasks: () => {
        const { tasks } = get();
        return tasks.filter((t) => t.status === 'COMPLETED');
      },
    }),
    {
      name: 'spark-tasks',
      storage: createJSONStorage(() => sessionStorage),
      partialize: (state) => ({
        tasks: state.tasks,
      }),
    }
  )
);
