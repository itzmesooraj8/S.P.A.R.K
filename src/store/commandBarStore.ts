/*
 * SPARK Command Bar Store (Zustand)
 * ────────────────────────────────────────────────────────────────────────────
 * Frontend state management for the Command Bar: open/close, context, history.
 */

import { create } from 'zustand';

export interface ContextItem {
  module: string;  // 'globe', 'security', 'music', etc.
  item_type: string;  // 'earthquake', 'alert', 'track', etc.
  label: string;  // Human-readable description
  data?: Record<string, unknown>;
}

export interface CommandBarStore {
  isOpen: boolean;
  setOpen: (open: boolean) => void;
  toggle: () => void;
  
  context: ContextItem | null;
  setContext: (context: ContextItem | null) => void;
  
  history: string[];
  addToHistory: (query: string) => void;
  clearHistory: () => void;
}

export const useCommandBarStore = create<CommandBarStore>((set) => ({
  isOpen: false,
  setOpen: (open) => set({ isOpen: open }),
  toggle: () => set((state) => ({ isOpen: !state.isOpen })),
  
  context: null,
  setContext: (context) => set({ context }),
  
  history: [],
  addToHistory: (query) => set((state) => ({
    history: [query, ...state.history.filter(h => h !== query)].slice(0, 50)  // Keep 50 items
  })),
  clearHistory: () => set({ history: [] }),
}));
