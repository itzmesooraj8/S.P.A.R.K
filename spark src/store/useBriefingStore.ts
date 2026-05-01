import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

export interface Briefing {
  id: string;
  title: string;
  content_text: string;
  content_audio_url?: string;
  generated_at: number;
  mood: string;
  tags: string[];
  meta?: Record<string, any>;
}

export interface BriefingStoreState {
  briefings: Briefing[];
  current: Briefing | null;
  loading: boolean;
  error: string | null;

  // Actions
  addBriefing: (briefing: Briefing) => void;
  updateBriefing: (id: string, updates: Partial<Briefing>) => void;
  removeBriefing: (id: string) => void;
  setBriefings: (briefings: Briefing[]) => void;
  setCurrent: (briefing: Briefing | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;

  // Selectors
  getBriefingById: (id: string) => Briefing | undefined;
  getLatest: () => Briefing | null;
}

export const useBriefingStore = create<BriefingStoreState>()(
  persist(
    (set, get) => ({
      briefings: [],
      current: null,
      loading: false,
      error: null,

      addBriefing: (briefing: Briefing) =>
        set((state) => ({
          briefings: [briefing, ...state.briefings],
          current: briefing,
        })),

      updateBriefing: (id: string, updates: Partial<Briefing>) =>
        set((state) => ({
          briefings: state.briefings.map((b) =>
            b.id === id ? { ...b, ...updates } : b
          ),
          current: state.current?.id === id ? { ...state.current, ...updates } : state.current,
        })),

      removeBriefing: (id: string) =>
        set((state) => ({
          briefings: state.briefings.filter((b) => b.id !== id),
          current: state.current?.id === id ? null : state.current,
        })),

      setBriefings: (briefings: Briefing[]) =>
        set(() => ({
          briefings,
        })),

      setCurrent: (briefing: Briefing | null) =>
        set(() => ({
          current: briefing,
        })),

      setLoading: (loading: boolean) =>
        set(() => ({
          loading,
        })),

      setError: (error: string | null) =>
        set(() => ({
          error,
        })),

      getBriefingById: (id: string) => {
        const { briefings } = get();
        return briefings.find((b) => b.id === id);
      },

      getLatest: () => {
        const { briefings } = get();
        return briefings.length > 0 ? briefings[0] : null;
      },
    }),
    {
      name: 'spark-briefings',
      storage: createJSONStorage(() => sessionStorage),
      partialize: (state) => ({
        briefings: state.briefings,
        current: state.current,
      }),
    }
  )
);
